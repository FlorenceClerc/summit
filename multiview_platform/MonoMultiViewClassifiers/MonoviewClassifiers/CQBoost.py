from ..Monoview.MonoviewUtils import CustomUniform, CustomRandint, BaseMonoviewClassifier
from ..Monoview.Additions.CQBoostUtils import ColumnGenerationClassifier
from ..Monoview.Additions.BoostUtils import getInterpretBase

import numpy as np
import os

class CQBoost(ColumnGenerationClassifier, BaseMonoviewClassifier):

    def __init__(self, random_state=None, mu=0.01, epsilon=1e-06, n_stumps=1, **kwargs):
        super(CQBoost, self).__init__(
            random_state=random_state,
            mu=mu,
            epsilon=epsilon
        )
        self.param_names = ["mu", "epsilon"]
        self.distribs = [CustomUniform(loc=0.5, state=1.0, multiplier="e-"),
                         CustomRandint(low=1, high=15, multiplier="e-")]
        self.classed_params = []
        self.weird_strings = {}
        self.n_stumps = n_stumps
        if "nbCores" not in kwargs:
            self.nbCores = 1
        else:
            self.nbCores = kwargs["nbCores"]

    def fit(self, X, y):
        if self.nbCores == 1:
            pass
        super(CQBoost, self).fit(X,y)
        if self.nbCores == 1:
            # os.environ['OMP_NUM_THREADS'] = num_threads
            pass


    def canProbas(self):
        """Used to know if the classifier can return label probabilities"""
        return True

    def getInterpret(self, directory, y_test):
        np.savetxt(directory + "train_metrics.csv", self.train_metrics, delimiter=',')
        np.savetxt(directory + "c_bounds.csv", self.c_bounds,
                   delimiter=',')
        np.savetxt(directory + "y_test_step.csv", self.step_decisions,
                   delimiter=',')
        step_metrics = []
        for step_index in range(self.step_decisions.shape[1] - 1):
            step_metrics.append(self.plotted_metric.score(y_test,
                                                          self.step_decisions[:,
                                                          step_index]))
        step_metrics = np.array(step_metrics)
        np.savetxt(directory + "step_test_metrics.csv", step_metrics,
                   delimiter=',')
        return getInterpretBase(self, directory, "CQBoost", self.weights_, y_test)


def formatCmdArgs(args):
    """Used to format kwargs for the parsed args"""
    kwargsDict = {"mu": args.CQB_mu,
                  "epsilon": args.CQB_epsilon,
                  "n_stumps":args.CQB_stumps}
    return kwargsDict


def paramsToSet(nIter, randomState):
    """Used for weighted linear early fusion to generate random search sets"""
    paramsSet = []
    for _ in range(nIter):
        paramsSet.append({"mu": 10**-randomState.uniform(0.5, 1.5),
                          "epsilon": 10**-randomState.randint(1, 15)})
    return paramsSet
