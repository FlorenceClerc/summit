#!/usr/bin/env python
# -*- encoding: utf-8

import numpy as np
from joblib import Parallel, delayed
from sklearn.multiclass import OneVsOneClassifier
from sklearn.svm import SVC

import MonoviewClassifiers
from utils.Dataset import getV


def fitMonoviewClassifier(classifierName, data, labels, classifierConfig):
    monoviewClassifier = getattr(MonoviewClassifiers, classifierName)
    classifier = monoviewClassifier.fit(data,labels,**dict((str(configIndex), config) for configIndex, config in
                                      enumerate(classifierConfig
                                                )))
    return classifier

def getAccuracies(LateFusionClassifiers):
    return ""


class LateFusionClassifier(object):
    def __init__(self, monoviewClassifiersNames, monoviewClassifiersConfigs, NB_CORES=1):
        self.monoviewClassifiersNames = monoviewClassifiersNames
        self.monoviewClassifiersConfigs = monoviewClassifiersConfigs
        self.monoviewClassifiers = []
        self.nbCores = NB_CORES
        self.accuracies = np.zeros(len(monoviewClassifiersNames))

    def fit_hdf5(self, DATASET, trainIndices=None):
        if trainIndices == None:
            trainIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
        nbView = DATASET.get("Metadata").attrs["nbView"]
        self.monoviewClassifiers = Parallel(n_jobs=self.nbCores)(
            delayed(fitMonoviewClassifier)(self.monoviewClassifiersNames[viewIndex],
                                              getV(DATASET, viewIndex, trainIndices),
                                              DATASET.get("Labels")[trainIndices],
                                              self.monoviewClassifiersConfigs[viewIndex])
            for viewIndex in range(nbView))