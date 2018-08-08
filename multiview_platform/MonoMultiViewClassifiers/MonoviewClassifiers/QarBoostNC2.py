import scipy
import logging
import numpy as np
import numpy.ma as ma
from collections import defaultdict
import math
from sklearn.utils.validation import check_is_fitted
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import time

from ..Monoview.MonoviewUtils import CustomUniform, CustomRandint
from ..Monoview.Additions.BoostUtils import StumpsClassifiersGenerator, sign, BaseBoost, getInterpretBase


class ColumnGenerationClassifierQarNC2(BaseEstimator, ClassifierMixin, BaseBoost):
    def __init__(self, epsilon=1e-06, n_max_iterations=None, estimators_generator=None, dual_constraint_rhs=0, save_iteration_as_hyperparameter_each=None, random_state=42):
        super(ColumnGenerationClassifierQarNC2, self).__init__()
        self.epsilon = epsilon
        self.n_max_iterations = n_max_iterations
        self.estimators_generator = estimators_generator
        self.dual_constraint_rhs = dual_constraint_rhs
        self.save_iteration_as_hyperparameter_each = save_iteration_as_hyperparameter_each
        self.random_state = random_state

    def fit(self, X, y):
        if scipy.sparse.issparse(X):
            logging.info('Converting to dense matrix.')
            X = np.array(X.todense())

        if self.estimators_generator is None:
            self.estimators_generator = StumpsClassifiersGenerator(n_stumps_per_attribute=self.n_stumps, self_complemented=False)

        y[y == 0] = -1

        self.estimators_generator.fit(X, y)
        self.classification_matrix = self._binary_classification_matrix(X)


        self.weights_ = []
        self.infos_per_iteration_ = defaultdict(list)

        m, n = self.classification_matrix.shape
        y_kernel_matrix = np.multiply(y.reshape((len(y), 1)), self.classification_matrix)

       # Initialization

        self.collected_weight_vectors_ = {}
        self.collected_dual_constraint_violations_ = {}

        self.example_weights = self._initialize_alphas(m).reshape((m,1))

        self.chosen_columns_ = []
        self.fobidden_columns = []
        self.edge_scores = []
        self.epsilons = []
        self.example_weights_ = [self.example_weights]
        self.train_accuracies = []
        self.previous_votes = []

        self.n_total_hypotheses_ = n
        self.n_total_examples = m

        for k in range(min(n, self.n_max_iterations if self.n_max_iterations is not None else np.inf)):
            # To choose the first voter, we select the one that has the best margin.
            if k == 0:
                first_voter_index = self._find_best_margin(y_kernel_matrix)
                self.chosen_columns_.append(first_voter_index)

                self.previous_vote = self.classification_matrix[:, first_voter_index].reshape((m,1))
                self.weighted_sum = self.classification_matrix[:, first_voter_index].reshape((m,1))

                epsilon = self._compute_epsilon()
                self.epsilons.append(epsilon)
                self.q = math.log((1-epsilon)/epsilon)
                self.weights_.append(self.q)

                self._update_example_weights(y)
                self.example_weights_.append(self.example_weights)
                self.train_accuracies.append(accuracy_score(y, np.sign(self.previous_vote)))
                continue

            # Find best weak hypothesis given example_weights. Select the one that has the lowest minimum
            # C-bound with the previous vote
            sol, new_voter_index = self._find_new_voter(y_kernel_matrix, y)
            if type(sol) == str:
                self.break_cause = " no more hypothesis were able to improve the boosted vote."
                break

            # Append the weak hypothesis.
            self.chosen_columns_.append(new_voter_index)
            self.weighted_sum = np.matmul(np.concatenate((self.previous_vote, self.classification_matrix[:, new_voter_index].reshape((m,1))), axis=1),
                                           sol).reshape((m,1))

            # Generate the new weight for the new voter
            epsilon = self._compute_epsilon()
            self.epsilons.append(epsilon)
            if epsilon == 0. or math.log((1 - epsilon) / epsilon) == math.inf:
                self.chosen_columns_.pop()
                self.break_cause = " epsilon was too small."
                break
            self.q = math.log((1 - epsilon) / epsilon)
            self.weights_.append(self.q)

            # Update the distribution on the examples.
            self._update_example_weights(y)
            self.example_weights_.append(self.example_weights)

            # Update the "previous vote" to prepare for the next iteration
            self.previous_vote = np.matmul(self.classification_matrix[:, self.chosen_columns_],
                                           np.array(self.weights_).reshape((k + 1, 1))).reshape((m, 1))/np.sum(self.weights_)
            self.previous_votes.append(self.previous_vote)
            self.train_accuracies.append(accuracy_score(y, np.sign(self.previous_vote)))

        self.nb_opposed_voters = self.check_opposed_voters()
        self.estimators_generator.estimators_ = self.estimators_generator.estimators_[self.chosen_columns_]
        self.weights_ = np.array(self.weights_)

        self.weights_/=np.sum(self.weights_)
        y[y == -1] = 0

        return self

    def predict(self, X):
        start = time.time()
        check_is_fitted(self, 'weights_')
        if scipy.sparse.issparse(X):
            logging.warning('Converting sparse matrix to dense matrix.')
            X = np.array(X.todense())
        classification_matrix = self._binary_classification_matrix(X)
        margins = np.squeeze(np.asarray(np.matmul(classification_matrix, self.weights_)))
        signs_array = np.array([int(x) for x in sign(margins)])
        signs_array[signs_array == -1] = 0
        end = time.time()
        self.predict_time = end - start
        return signs_array

    def _compute_epsilon(self,):
        """Updating the \epsilon varaible"""
        ones_matrix = np.zeros(self.weighted_sum.shape)
        ones_matrix[self.weighted_sum < 0] = 1
        epsilon = (1.0/self.n_total_examples)*np.sum(self.example_weights*ones_matrix, axis=0)
        return epsilon

    def _find_best_margin(self, y_kernel_matrix):
        """Used only on the first iteration to select the voter with the largest margin"""
        pseudo_h_values = ma.array(np.sum(y_kernel_matrix, axis=0), fill_value=-np.inf)
        pseudo_h_values[self.fobidden_columns] = ma.masked
        worst_h_index = ma.argmax(pseudo_h_values)
        return worst_h_index

    def _find_new_voter(self, y_kernel_matrix, y):
        """Here, we solve the two_voters_mincq_problem for each potential new voter,
        and select the one that has the smallest minimum"""
        c_borns = []
        possible_sols = []
        indices = []
        for hypothese_index, hypothese in enumerate(y_kernel_matrix.transpose()):
            causes = []
            w = self._solve_two_weights_min_c(hypothese, y)
            if w[0] != "break":
                c_borns.append(self._cbound(w[0]))
                possible_sols.append(w)
                indices.append(hypothese_index)
            else:
                causes.append(w[1])
        if c_borns:
            min_c_born_index = ma.argmin(c_borns)
            selected_sol = possible_sols[min_c_born_index]
            selected_voter_index = indices[min_c_born_index]
            return selected_sol, selected_voter_index
        else:
            return "break", "smthng"

    def _update_example_weights(self, y):
        new_weights = self.example_weights*np.exp(-self.q*y.reshape((self.n_total_examples, 1))*self.weighted_sum)
        self.example_weights = new_weights/np.sum(new_weights)

    def _solve_two_weights_min_c(self, next_column, y):
        """Here we solve the min C-bound problem for two voters and return the best 2-weights array"""
        m = next_column.shape[0]
        zero_diag = np.ones((m, m)) - np.identity(m)

        weighted_previous_sum = np.multiply(np.multiply(y.reshape((m, 1)), self.previous_vote.reshape((m, 1))), self.example_weights.reshape((m,1)))
        weighted_next_column = np.multiply(next_column.reshape((m,1)), self.example_weights.reshape((m,1)))

        mat_prev = np.repeat(weighted_previous_sum, m, axis=1) * zero_diag
        mat_next = np.repeat(weighted_next_column, m, axis=1) * zero_diag

        self.B2 = np.sum((weighted_previous_sum - weighted_next_column) ** 2)
        self.B1 = np.sum(2 * weighted_next_column * (weighted_previous_sum - 2 * weighted_next_column * weighted_next_column))
        self.B0 = np.sum(weighted_next_column * weighted_next_column)

        self.A2 = self.B2 + np.sum((mat_prev - mat_next) * np.transpose(mat_prev - mat_next))
        self.A1 = self.B1 + np.sum(mat_prev * np.transpose(mat_next) - mat_next * np.transpose(mat_prev) - 2 * mat_next * np.transpose(mat_next))
        self.A0 = self.B0 + np.sum(mat_next * np.transpose(mat_next))
        C2 = (self.A1 * self.B2 - self.A2 * self.B1)
        C1 = 2 * (self.A0 * self.B2 - self.A2 * self.B0)
        C0 = self.A0 * self.B1 - self.A1 * self.B0

        if C2 == 0:
            if C1 == 0:
                return np.array([0.5, 0.5])
            elif abs(C1) > 0:
                return np.array([0., 1.])
            else:
                return ['break', "the derivate was constant."]
        elif C2 == 0:
            return ["break", "the derivate was affine."]
        try:
            sols = np.roots(np.array([C2, C1, C0]))
        except:
            return ["break", "nan"]

        is_acceptable, sol = self._analyze_solutions(sols)
        if is_acceptable:
            return np.array([sol, 1-sol])
        else:
            return ["break", sol]

    def _analyze_solutions(self, sols):
        """"We just check that the solution found by np.roots is acceptable under our constraints
        (real, a minimum and between 0 and 1)"""
        for sol_index, sol in enumerate(sols):
            if isinstance(sol, complex):
                sols[sol_index] = -1
        if sols.shape[0] == 1:
            if self._cbound(sols[0]) < self._cbound(sols[0] + 1):
                best_sol = sols[0]
            else:
                return False, " the only solution was a maximum."
        elif sols.shape[0] == 2:
            best_sol = self._best_sol(sols)
        else:
            return False, " no solution were found."

        if 0 < best_sol < 1:
            return True, self._best_sol(sols)

        elif best_sol <= 0:
            return False, " the minimum was below 0."
        else:
            return False, " the minimum was over 1."

    def _cbound(self, sol):
        """Computing the objective function"""
        return 1 - (self.A2*sol**2 + self.A1*sol + self.A0)/(self.B2*sol**2 + self.B1*sol + self.B0)

    def _best_sol(self, sols):
        values = np.array([self._cbound(sol) for sol in sols])
        return sols[np.argmin(values)]



class QarBoostNC2Classifier(ColumnGenerationClassifierQarNC2):
    def __init__(self, mu=0.001, epsilon=1e-08, n_max_iterations=None, estimators_generator=None, save_iteration_as_hyperparameter_each=None, random_state=42):
        super(QarBoostNC2Classifier, self).__init__(epsilon, n_max_iterations, estimators_generator, dual_constraint_rhs=0,
                                                    save_iteration_as_hyperparameter_each=save_iteration_as_hyperparameter_each, random_state=random_state)
        self.mu = mu
        self.train_time = 0

    def _initialize_alphas(self, n_examples):
        return 1.0 / n_examples * np.ones((n_examples,))


class QarBoostNC2(QarBoostNC2Classifier):

    def __init__(self, random_state, **kwargs):
        super(QarBoostNC2, self).__init__(
            mu=kwargs['mu'],
            epsilon=kwargs['epsilon'],
            n_max_iterations= kwargs['n_max_iterations'],
            random_state = random_state)

    def canProbas(self):
        """Used to know if the classifier can return label probabilities"""
        return False

    def paramsToSrt(self, nIter=1):
        """Used for weighted linear early fusion to generate random search sets"""
        paramsSet = []
        for _ in range(nIter):
            paramsSet.append({"mu": 0.001,
                              "epsilon": 1e-08,
                              "n_max_iterations": None})
        return paramsSet

    def getKWARGS(self, args):
        """Used to format kwargs for the parsed args"""
        kwargsDict = {}
        kwargsDict['mu'] = 0.001
        kwargsDict['epsilon'] = 1e-08
        kwargsDict['n_max_iterations'] = None
        return kwargsDict

    def genPipeline(self):
        return Pipeline([('classifier', QarBoostNC2Classifier())])

    def genParamsDict(self, randomState):
        return {"classifier__mu": [0.001],
                "classifier__epsilon": [1e-08],
                "classifier__n_max_iterations": [None]}

    def genBestParams(self, detector):
        return {"mu": detector.best_params_["classifier__mu"],
                "epsilon": detector.best_params_["classifier__epsilon"],
                "n_max_iterations": detector.best_params_["classifier__n_max_iterations"]}

    def genParamsFromDetector(self, detector):
        nIter = len(detector.cv_results_['param_classifier__mu'])
        return [("mu", np.array([0.001 for _ in range(nIter)])),
                ("epsilon", np.array(detector.cv_results_['param_classifier__epsilon'])),
                ("n_max_iterations", np.array(detector.cv_results_['param_classifier__n_max_iterations']))]

    def getConfig(self, config):
        if type(config) is not dict:  # Used in late fusion when config is a classifier
            return "\n\t\t- QarBoost with mu : " + str(config.mu) + ", epsilon : " + str(
                config.epsilon + ", n_max_iterations : " + str(config.n_max_iterations))
        else:
            return "\n\t\t- QarBoost with mu : " + str(config["mu"]) + ", epsilon : " + str(
                   config["epsilon"] + ", n_max_iterations : " + str(config["n_max_iterations"]))


    def getInterpret(self, classifier, directory):
        interpretString = ""
        return interpretString


def canProbas():
    return False


def fit(DATASET, CLASS_LABELS, randomState, NB_CORES=1, **kwargs):
    start =time.time()
    """Used to fit the monoview classifier with the args stored in kwargs"""
    classifier = QarBoostNC2Classifier(mu=kwargs['mu'],
                                       epsilon=kwargs['epsilon'],
                                       n_max_iterations=kwargs["n_max_iterations"],
                                       random_state=randomState)
    classifier.fit(DATASET, CLASS_LABELS)
    end = time.time()
    classifier.train_time = end-start
    return classifier


def paramsToSet(nIter, randomState):
    """Used for weighted linear early fusion to generate random search sets"""
    paramsSet = []
    for _ in range(nIter):
        paramsSet.append({"mu": randomState.uniform(1e-02, 10**(-0.5)),
                          "epsilon": 10**-randomState.randint(1, 15),
                          "n_max_iterations": None})
    return paramsSet


def getKWARGS(args):
    """Used to format kwargs for the parsed args"""
    kwargsDict = {}
    kwargsDict['mu'] = args.QarBNC2_mu
    kwargsDict['epsilon'] = args.QarBNC2_epsilon
    kwargsDict['n_max_iterations'] = None
    return kwargsDict


def genPipeline():
    return Pipeline([('classifier', QarBoostNC2Classifier())])


def genParamsDict(randomState):
    return {"classifier__mu": CustomUniform(loc=.5, state=2, multiplier='e-'),
            "classifier__epsilon": CustomRandint(low=1, high=15, multiplier='e-'),
            "classifier__n_max_iterations": [None],
            "classifier__random_state":[randomState]}


def genBestParams(detector):
    return {"mu": detector.best_params_["classifier__mu"],
                "epsilon": detector.best_params_["classifier__epsilon"],
                "n_max_iterations": detector.best_params_["classifier__n_max_iterations"]}


def genParamsFromDetector(detector):
    nIter = len(detector.cv_results_['param_classifier__mu'])
    return [("mu", np.array(detector.cv_results_['param_classifier__mu'])),
            ("epsilon", np.array(detector.cv_results_['param_classifier__epsilon'])),
            ("n_max_iterations", np.array(detector.cv_results_['param_classifier__n_max_iterations']))]


def getConfig(config):
    if type(config) is not dict:  # Used in late fusion when config is a classifier
        return "\n\t\t- QarBoost with mu : " + str(config.mu) + ", epsilon : " + str(
            config.epsilon) + ", n_max_iterations : " + str(config.n_max_iterations)
    else:
        return "\n\t\t- QarBoost with mu : " + str(config["mu"]) + ", epsilon : " + str(
            config["epsilon"]) + ", n_max_iterations : " + str(config["n_max_iterations"])


def getInterpret(classifier, directory):
    return getInterpretBase(classifier, directory, "QarBoost", classifier.weights_, classifier.break_cause)
