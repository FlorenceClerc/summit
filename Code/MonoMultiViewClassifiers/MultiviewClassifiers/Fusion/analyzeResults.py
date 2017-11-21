from sklearn.metrics import precision_recall_fscore_support, accuracy_score, classification_report
import numpy as np
import matplotlib

# matplotlib.use('Agg')
import operator
from .Methods import LateFusion
from ... import Metrics

# Author-Info
__author__ = "Baptiste Bauvin"
__status__ = "Prototype"  # Production, Development, Prototype


def printMetricScore(metricScores, metrics):
    metricScoreString = "\n\n"
    for metric in metrics:
        metricModule = getattr(Metrics, metric[0])
        if metric[1] is not None:
            metricKWARGS = dict((index, metricConfig) for index, metricConfig in enumerate(metric[1]))
        else:
            metricKWARGS = {}
        metricScoreString += "\tFor " + metricModule.getConfig(**metricKWARGS) + " : "
        metricScoreString += "\n\t\t- Score on train : " + str(metricScores[metric[0]][0])
        metricScoreString += "\n\t\t- Score on test : " + str(metricScores[metric[0]][1])
        metricScoreString += "\n\n"
    return metricScoreString


def getTotalMetricScores(metric, trainLabels, testLabels, validationIndices, learningIndices, labels):
    metricModule = getattr(Metrics, metric[0])
    if metric[1] is not None:
        metricKWARGS = dict((index, metricConfig) for index, metricConfig in enumerate(metric[1]))
    else:
        metricKWARGS = {}
    try:
        trainScore = metricModule.score(labels[learningIndices], trainLabels, **metricKWARGS)
    except:
        print(labels[learningIndices])
        print(trainLabels)
        import pdb;pdb.set_trace()
    testScore = metricModule.score(labels[validationIndices], testLabels, **metricKWARGS)
    return [trainScore, testScore]


def getMetricsScores(metrics, trainLabels, testLabels,
                     validationIndices, learningIndices, labels):
    metricsScores = {}
    for metric in metrics:
        metricsScores[metric[0]] = getTotalMetricScores(metric, trainLabels, testLabels,
                                                        validationIndices, learningIndices, labels)
    return metricsScores


def execute(classifier, trainLabels,
            testLabels, DATASET,
            classificationKWARGS, classificationIndices,
            LABELS_DICTIONARY, views, nbCores, times,
            name, KFolds,
            hyperParamSearch, nIter, metrics,
            viewsIndices, randomState, labels):
    CLASS_LABELS = labels

    fusionType = classificationKWARGS["fusionType"]
    monoviewClassifiersNames = classificationKWARGS["classifiersNames"]
    monoviewClassifiersConfigs = classificationKWARGS["classifiersConfigs"]
    fusionMethodConfig = classificationKWARGS["fusionMethodConfig"]

    learningIndices, validationIndices, testIndicesMulticlass = classificationIndices
    metricModule = getattr(Metrics, metrics[0][0])
    if metrics[0][1] is not None:
        metricKWARGS = dict((index, metricConfig) for index, metricConfig in enumerate(metrics[0][1]))
    else:
        metricKWARGS = {}
    scoreOnTrain = metricModule.score(CLASS_LABELS[learningIndices], CLASS_LABELS[learningIndices], **metricKWARGS)
    scoreOnTest = metricModule.score(CLASS_LABELS[validationIndices], testLabels, **metricKWARGS)
    fusionConfiguration = classifier.classifier.getConfig(fusionMethodConfig, monoviewClassifiersNames,
                                                          monoviewClassifiersConfigs)
    stringAnalysis = "\t\tResult for Multiview classification with " + fusionType + " and random state : " + str(
        randomState) + \
                     "\n\n" + metrics[0][0] + " :\n\t-On Train : " + str(scoreOnTrain) + "\n\t-On Test : " + str(
        scoreOnTest) + \
                     "\n\nDataset info :\n\t-Database name : " + name + "\n\t-Labels : " + \
                     ', '.join(LABELS_DICTIONARY.values()) + "\n\t-Views : " + ', '.join(views) + "\n\t-" + str(
        KFolds.n_splits) + \
                     " folds\n\nClassification configuration : \n\t-Algorithm used : " + fusionType + " " + fusionConfiguration

    if fusionType == "LateFusion":
        stringAnalysis += LateFusion.getScores(classifier)
    metricsScores = getMetricsScores(metrics, trainLabels, testLabels,
                                     validationIndices, learningIndices, labels)
    stringAnalysis += printMetricScore(metricsScores, metrics)

    imagesAnalysis = {}
    return stringAnalysis, imagesAnalysis, metricsScores