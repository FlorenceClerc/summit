from ...Methods.EarlyFusion import EarlyFusionClassifier
import MonoviewClassifiers
import numpy as np
from sklearn.metrics import accuracy_score


def gridSearch(DATASET, classificationKWARGS, trainIndices, nIter=30, viewsIndices=None):
    if type(viewsIndices)==type(None):
        viewsIndices = np.arange(DATASET.get("Metadata").attrs["nbView"])
    nbView = len(viewsIndices)
    bestScore = 0.0
    bestConfig = None
    if classificationKWARGS["fusionMethodConfig"][0] is not None:
        for i in range(nIter):
            randomWeightsArray = np.random.random_sample(nbView)
            normalizedArray = randomWeightsArray/np.sum(randomWeightsArray)
            classificationKWARGS["fusionMethodConfig"][0] = normalizedArray
            classifier = WeightedLinear(1, **classificationKWARGS)
            classifier.fit_hdf5(DATASET, trainIndices, viewsIndices=viewsIndices)
            predictedLabels = classifier.predict_hdf5(DATASET, trainIndices, viewsIndices=viewsIndices)
            accuracy = accuracy_score(DATASET.get("Labels")[trainIndices], predictedLabels)
            if accuracy > bestScore:
                bestScore = accuracy
                bestConfig = normalizedArray
        return [np.array([1.0 for i in range(nbView)])]


class WeightedLinear(EarlyFusionClassifier):
    def __init__(self, NB_CORES=1, **kwargs):
        EarlyFusionClassifier.__init__(self, kwargs['classifiersNames'], kwargs['classifiersConfigs'],
                                       NB_CORES=NB_CORES)
        self.weights = np.array(map(float, kwargs['fusionMethodConfig'][0]))

    def fit_hdf5(self, DATASET, trainIndices=None, viewsIndices=None):
        if type(viewsIndices)==type(None):
            viewsIndices = np.arange(DATASET.get("Metadata").attrs["nbView"])
        if not trainIndices:
            trainIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
        self.weights = self.weights/float(max(self.weights))
        self.makeMonoviewData_hdf5(DATASET, weights=self.weights, usedIndices=trainIndices, viewsIndices=viewsIndices)
        monoviewClassifierModule = getattr(MonoviewClassifiers, self.monoviewClassifierName)
        self.monoviewClassifier = monoviewClassifierModule.fit(self.monoviewData, DATASET.get("Labels")[trainIndices],
                                                                     NB_CORES=self.nbCores, #**self.monoviewClassifiersConfig)
                                                                     **self.monoviewClassifiersConfig)

    def predict_hdf5(self, DATASET, usedIndices=None, viewsIndices=None):
        if type(viewsIndices)==type(None):
            viewsIndices = np.arange(DATASET.get("Metadata").attrs["nbView"])
        self.weights = self.weights/float(max(self.weights))
        if usedIndices == None:
            usedIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
        if usedIndices:
            self.makeMonoviewData_hdf5(DATASET, weights=self.weights, usedIndices=usedIndices, viewsIndices=viewsIndices)
            predictedLabels = self.monoviewClassifier.predict(self.monoviewData)
        else:
            predictedLabels=[]
        return predictedLabels

    def predict_proba_hdf5(self, DATASET, usedIndices=None):
        if usedIndices == None:
            usedIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
        if usedIndices:
            self.makeMonoviewData_hdf5(DATASET, weights=self.weights, usedIndices=usedIndices)
            predictedLabels = self.monoviewClassifier.predict_proba(self.monoviewData)
        else:
            predictedLabels=[]
        return predictedLabels

    def getConfig(self, fusionMethodConfig ,monoviewClassifiersNames, monoviewClassifiersConfigs):
        configString = "with weighted concatenation, using weights : "+", ".join(map(str, self.weights))+ \
                       " with monoview classifier : "
        monoviewClassifierModule = getattr(MonoviewClassifiers, monoviewClassifiersNames[0])
        configString += monoviewClassifierModule.getConfig(monoviewClassifiersConfigs[0])
        return configString

    def gridSearch(self, classificationKWARGS):

        return