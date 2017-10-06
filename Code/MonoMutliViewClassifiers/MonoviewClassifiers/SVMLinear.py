from sklearn.svm import SVC
from sklearn.pipeline import Pipeline                   # Pipelining in classification
from sklearn.model_selection import RandomizedSearchCV
import Metrics
from scipy.stats import randint


# Author-Info
__author__ 	= "Baptiste Bauvin"
__status__ 	= "Prototype"                           # Production, Development, Prototype


def canProbas():
    return True


def fit(DATASET, CLASS_LABELS, randomState, NB_CORES=1,**kwargs):
    C = int(kwargs['0'])
    classifier = SVC(C=C, kernel='linear', probability=True, max_iter=1000, random_state=randomState)
    classifier.fit(DATASET, CLASS_LABELS)
    return classifier


def paramsToSet(nIter, randomState):
    paramsSet = []
    for _ in range(nIter):
        paramsSet.append([randomState.randint(1, 10000),])
    return paramsSet


def getKWARGS(kwargsList):
    kwargsDict = {}
    for (kwargName, kwargValue) in kwargsList:
        if kwargName == "CL_SVMLinear_C":
            kwargsDict['0'] = int(kwargValue)
    return kwargsDict


def randomizedSearch(X_train, y_train, randomState, KFolds=4, nbCores=1, metric=["accuracy_score", None], nIter=30):
    pipeline_SVMLinear = Pipeline([('classifier', SVC(kernel="linear", max_iter=1000))])
    param_SVMLinear = {"classifier__C": randint(1, 10000)}
    metricModule = getattr(Metrics, metric[0])
    if metric[1]!=None:
        metricKWARGS = dict((index, metricConfig) for index, metricConfig in enumerate(metric[1]))
    else:
        metricKWARGS = {}
    scorer = metricModule.get_scorer(**metricKWARGS)
    grid_SVMLinear = RandomizedSearchCV(pipeline_SVMLinear, n_iter=nIter, param_distributions=param_SVMLinear,
                                        refit=True, n_jobs=nbCores, scoring=scorer, cv=KFolds,
                                        random_state=randomState)

    SVMLinear_detector = grid_SVMLinear.fit(X_train, y_train)
    desc_params = [SVMLinear_detector.best_params_["classifier__C"]]
    return desc_params


def getConfig(config):
    if type(config) not in [list, dict]:
        return "\n\t\t- SVM Linear with C : "+str(config.C)
    else:
        try:
            return "\n\t\t- SVM Linear with C : "+str(config[0])
        except:
            return "\n\t\t- SVM Linear with C : "+str(config["0"])
