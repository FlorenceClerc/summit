import numpy as np
from pyscm.scm import SetCoveringMachineClassifier as scm
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.externals.six import iteritems


def genName(config):
    return "FatSCMLateFusion"


def getBenchmark(benchmark, args=None):
    benchmark["Multiview"]["FatSCMLateFusion"] = ["take_everything"]
    return benchmark


def getArgs(args, benchmark, views, viewsIndices, randomState, directory, resultsMonoview, classificationIndices):
    argumentsList = []
    monoviewDecisions = np.transpose(np.array([monoviewResult[1][3] for monoviewResult in resultsMonoview]))
    arguments = {"CL_type": "FatSCMLateFusion",
                 "views": ["all"],
                 "NB_VIEW": len(resultsMonoview),
                 "viewsIndices": range(len(resultsMonoview)),
                 "NB_CLASS": len(args.CL_classes),
                 "LABELS_NAMES": args.CL_classes,
                 "FatSCMLateFusionKWARGS": {
                     "monoviewDecisions": monoviewDecisions,
                     "p": args.FSCMLF_p,
                     "max_attributes": args.FSCMLF_max_attributes,
                     "model":args.FSCMLF_model,
                 }
                 }
    argumentsList.append(arguments)
    return argumentsList


def genParamsSets(classificationKWARGS, randomState, nIter=1):
    """Used to generate parameters sets for the random hyper parameters optimization function"""
    paramsSets = []
    for _ in range(nIter):
        max_attributes = randomState.randint(1, 20)
        p = randomState.random_sample()
        model = randomState.choice(["conjunction", "disjunction"])
        paramsSets.append([p, max_attributes, model])

    return paramsSets


class FatSCMLateFusionClass:

    def __init__(self, randomState, NB_CORES=1, **kwargs):
        if kwargs["p"]:
            self.p = kwargs["p"]
        else:
            self.p = 0.5
        if kwargs["max_attributes"]:
            self.max_attributes = kwargs["max_attributes"]
        else:
            self.max_attributes = 5
        if kwargs["model"]:
            self.model = kwargs["model"]
        else:
            self.model = "conjunction"
        self.monoviewDecisions = kwargs["monoviewDecisions"]
        self.randomState = randomState

    def setParams(self, paramsSet):
        self.p = paramsSet[0]
        self.max_attributes = paramsSet[1]
        self.model = paramsSet[2]

    def fit_hdf5(self, DATASET, labels, trainIndices=None, viewsIndices=None, metric=["f1_score", None]):
        features = self.monoviewDecisions[trainIndices]
        self.SCMClassifier = DecisionStumpSCMNew(p=self.p, max_rules=self.max_attributes, model_type=self.model,
                                                 random_state=self.randomState)
        self.SCMClassifier.fit(features, labels[trainIndices].astype(int))

    def predict_hdf5(self, DATASET, usedIndices=None, viewsIndices=None):
        if usedIndices is None:
            usedIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
        predictedLabels = self.SCMClassifier.predict(self.monoviewDecisions[usedIndices])
        return predictedLabels

    def predict_probas_hdf5(self, DATASET, usedIndices=None):
        pass

    def getConfigString(self, classificationKWARGS):
        return "p : "+str(self.p)+", max_aributes : "+str(self.max_attributes)+", model : "+self.model

    def getSpecificAnalysis(self, classificationKWARGS):
        stringAnalysis = 'Rules used : ' + str(self.SCMClassifier.clf.model_)
        return stringAnalysis


class DecisionStumpSCMNew(BaseEstimator, ClassifierMixin):
    """docstring for SCM
    A hands on class of SCM using decision stump, built with sklearn format in order to use sklearn function on SCM like
    CV, gridsearch, and so on ..."""

    def __init__(self, model_type='conjunction', p=0.1, max_rules=10, random_state=42):
        super(DecisionStumpSCMNew, self).__init__()
        self.model_type = model_type
        self.p = p
        self.max_rules = max_rules
        self.random_state = random_state

    def fit(self, X, y):
        self.clf = scm(model_type=self.model_type, max_rules=self.max_rules, p=self.p, random_state=self.random_state)
        self.clf.fit(X=X, y=y)

    def predict(self, X):
        return self.clf.predict(X)

    def set_params(self, **params):
        for key, value in iteritems(params):
            if key == 'p':
                self.p = value
            if key == 'model_type':
                self.model_type = value
            if key == 'max_rules':
                self.max_rules = value

    def get_stats(self):
        return {"Binary_attributes": self.clf.model_.rules}
