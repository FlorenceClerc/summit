from sklearn.svm import SVC
from sklearn.pipeline import Pipeline                   # Pipelining in classification
from sklearn.grid_search import GridSearchCV
import numpy as np
import Metrics


def fit(DATASET, CLASS_LABELS, NB_CORES=1,**kwargs):
    C = int(kwargs['0'])
    classifier = SVC(C=C, kernel='rbf', probability=True)
    classifier.fit(DATASET, CLASS_LABELS)
    return "No desc", classifier


# def fit_gridsearch(X_train, y_train, nbFolds=4, nbCores=1, metric=["accuracy_score", None], **kwargs):
#     pipeline_SVMRBF = Pipeline([('classifier', SVC(kernel="rbf"))])
#     param_SVMRBF = {"classifier__C": map(int, kwargs['0'])}
#     metricModule = getattr(Metrics, metric[0])
#     scorer = metricModule.get_scorer(dict((index, metricConfig) for index, metricConfig in enumerate(metric[1])))
#     grid_SVMRBF = GridSearchCV(pipeline_SVMRBF, param_grid=param_SVMRBF, refit=True, n_jobs=nbCores, scoring='accuracy',
#                                cv=nbFolds)
#     SVMRBF_detector = grid_SVMRBF.fit(X_train, y_train)
#     desc_params = [SVMRBF_detector.best_params_["classifier__C"]]
#     description = "Classif_" + "SVC" + "-" + "CV_" + str(nbFolds) + "-" + "-".join(map(str,desc_params))
#     return description, SVMRBF_detector


def gridSearch(X_train, y_train, nbFolds=4, nbCores=1, metric=["accuracy_score", None], **kwargs):
    pipeline_SVMRBF = Pipeline([('classifier', SVC(kernel="rbf"))])
    param_SVMRBF = {"classifier__C": np.random.randint(1,2000,30)}
    metricModule = getattr(Metrics, metric[0])
    scorer = metricModule.get_scorer(dict((index, metricConfig) for index, metricConfig in enumerate(metric[1])))
    grid_SVMRBF = GridSearchCV(pipeline_SVMRBF, param_grid=param_SVMRBF, refit=True, n_jobs=nbCores, scoring='accuracy',
                               cv=nbFolds)
    SVMRBF_detector = grid_SVMRBF.fit(X_train, y_train)
    desc_params = [SVMRBF_detector.best_params_["classifier__C"]]
    return desc_params


def getConfig(config):
    return "\n\t\t- SVM with C : "+config[0]+", kernel : "+config[1]