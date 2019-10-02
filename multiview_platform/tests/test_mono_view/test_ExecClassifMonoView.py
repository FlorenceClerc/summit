import os
import unittest

import h5py
import numpy as np
from sklearn.model_selection import StratifiedKFold

from ..utils import rm_tmp

from ...mono_multi_view_classifiers.monoview import exec_classif_mono_view
from ...mono_multi_view_classifiers.monoview_classifiers import decision_tree


class Test_initConstants(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rm_tmp()
        os.mkdir("multiview_platform/tests/temp_tests")
        cls.datasetFile = h5py.File(
            "multiview_platform/tests/temp_tests/test.hdf5", "w")
        cls.random_state = np.random.RandomState(42)
        cls.args = {"classifier_name": "test_clf"}
        cls.X_value = cls.random_state.randint(0, 500, (10, 20))
        cls.X = cls.datasetFile.create_dataset("View0", data=cls.X_value)
        cls.X.attrs["name"] = "test_dataset"
        cls.X.attrs["sparse"] = False
        cls.classificationIndices = [np.array([0, 2, 4, 6, 8]),
                                     np.array([1, 3, 5, 7, 9]),
                                     np.array([1, 3, 5, 7, 9])]
        cls.labelsNames = ["test_true", "test_false"]
        cls.name = "test"
        cls.directory = "multiview_platform/tests/temp_tests/test_dir/"

    def test_simple(cls):
        kwargs, \
        t_start, \
        feat, \
        CL_type, \
        X, \
        learningRate, \
        labelsString, \
        outputFileName = exec_classif_mono_view.initConstants(cls.args,
                                                              cls.X,
                                                              cls.classificationIndices,
                                                              cls.labelsNames,
                                                              cls.name,
                                                              cls.directory)
        cls.assertEqual(kwargs, cls.args)
        cls.assertEqual(feat, "test_dataset")
        cls.assertEqual(CL_type, "test_clf")
        np.testing.assert_array_equal(X, cls.X_value)
        cls.assertEqual(learningRate, 0.5)
        cls.assertEqual(labelsString, "test_true-test_false")
        # cls.assertEqual(outputFileName, "Code/tests/temp_tests/test_dir/test_clf/test_dataset/results-test_clf-test_true-test_false-learnRate0.5-test-test_dataset-")

    @classmethod
    def tearDownClass(cls):
        os.remove("multiview_platform/tests/temp_tests/test.hdf5")
        os.rmdir(
            "multiview_platform/tests/temp_tests/test_dir/test_clf/test_dataset")
        os.rmdir("multiview_platform/tests/temp_tests/test_dir/test_clf")
        os.rmdir("multiview_platform/tests/temp_tests/test_dir")
        os.rmdir("multiview_platform/tests/temp_tests")


class Test_initTrainTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rm_tmp()
        cls.random_state = np.random.RandomState(42)
        cls.X = cls.random_state.randint(0, 500, (10, 5))
        cls.Y = cls.random_state.randint(0, 2, 10)
        cls.classificationIndices = [np.array([0, 2, 4, 6, 8]),
                                     np.array([1, 3, 5, 7, 9]),
                                     np.array([1, 3, 5, 7, 9])]

    def test_simple(cls):
        X_train, y_train, X_test, y_test, X_test_multiclass = exec_classif_mono_view.init_train_test(
            cls.X, cls.Y, cls.classificationIndices)
        np.testing.assert_array_equal(X_train, np.array(
            [np.array([102, 435, 348, 270, 106]),
             np.array([466, 214, 330, 458, 87]),
             np.array([149, 308, 257, 343, 491]),
             np.array([276, 160, 459, 313, 21]),
             np.array([58, 169, 475, 187, 463])]))
        np.testing.assert_array_equal(X_test, np.array(
            [np.array([71, 188, 20, 102, 121]),
             np.array([372, 99, 359, 151, 130]),
             np.array([413, 293, 385, 191, 443]),
             np.array([252, 235, 344, 48, 474]),
             np.array([270, 189, 445, 174, 445])]))
        np.testing.assert_array_equal(y_train, np.array([0, 0, 1, 0, 0]))
        np.testing.assert_array_equal(y_test, np.array([1, 1, 0, 0, 0]))


class Test_getHPs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rm_tmp()
        os.mkdir("multiview_platform/tests/tmp_tests")
        cls.classifierModule = decision_tree
        cls.hyperParamSearch = "randomized_search"
        cls.n_iter = 2
        cls.classifier_name = "decision_tree"
        cls.random_state = np.random.RandomState(42)
        cls.X = cls.random_state.randint(0,10,size=(10,5))
        cls.y = cls.random_state.randint(0,2,size=10)
        cls.output_file_name = "multiview_platform/tests/tmp_tests/"
        cls.cv = StratifiedKFold(n_splits=2, random_state=cls.random_state)
        cls.nb_cores = 1
        cls.metrics = [["accuracy_score", None]]
        cls.kwargs = {"decision_tree" : {"max_depth": 1,
                      "criterion": "gini",
                      "splitter": "best"}}
        cls.classifier_class_name = "DecisionTree"

    @classmethod
    def tearDownClass(cls):
        for file_name in os.listdir("multiview_platform/tests/tmp_tests"):
            os.remove(
                os.path.join("multiview_platform/tests/tmp_tests", file_name))
        os.rmdir("multiview_platform/tests/tmp_tests")

    def test_simple(self):
        kwargs, test_folds_predictions = exec_classif_mono_view.getHPs(self.classifierModule,
                                                                       self.hyperParamSearch,
                                                                       self.n_iter,
                                                                       self.classifier_name,
                                                                       self.classifier_class_name,
                                                                       self.X,
                                                                       self.y,
                                                                       self.random_state,
                                                                       self.output_file_name,
                                                                       self.cv,
                                                                       self.nb_cores,
                                                                       self.metrics,
                                                                       self.kwargs)

# class Test_getKWARGS(unittest.TestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         cls.classifierModule = None
#         cls.hyperParamSearch = "None"
#         cls.nIter = 2
#         cls.CL_type = "string"
#         cls.X_train = np.zeros((10,20))
#         cls.y_train = np.zeros((10))
#         cls.randomState = np.random.RandomState(42)
#         cls.outputFileName = "test_file"
#         cls.KFolds = None
#         cls.nbCores = 1
#         cls.metrics = {"accuracy_score":""}
#         cls.kwargs = {}
#
#     def test_simple(cls):
#         clKWARGS = ExecClassifMonoView.getHPs(cls.classifierModule,
#                                               cls.hyperParamSearch,
#                                               cls.nIter,
#                                               cls.CL_type,
#                                               cls.X_train,
#                                               cls.y_train,
#                                               cls.randomState,
#                                               cls.outputFileName,
#                                               cls.KFolds,
#                                               cls.nbCores,
#                                               cls.metrics,
#                                               cls.kwargs)
#         pass
#
# class Test_saveResults(unittest.TestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         cls.stringAnalysis = "string analysis"
#         cls.outputFileName = "test_file"
#         cls.full_labels_pred = np.zeros(10)
#         cls.y_train_pred = np.ones(5)
#         cls.y_train = np.zeros(5)
#         cls.imagesAnalysis = {}
#
#     def test_simple(cls):
#         ExecClassifMonoView.saveResults(cls.stringAnalysis,
#                                         cls.outputFileName,
#                                         cls.full_labels_pred,
#                                         cls.y_train_pred,
#                                         cls.y_train,
#                                         cls.imagesAnalysis)
#         # Test if the files are created with the right content
#
#     def test_with_image_analysis(cls):
#         cls.imagesAnalysis = {"test_image":"image.png"} # Image to gen
#         ExecClassifMonoView.saveResults(cls.stringAnalysis,
#                                         cls.outputFileName,
#                                         cls.full_labels_pred,
#                                         cls.y_train_pred,
#                                         cls.y_train,
#                                         cls.imagesAnalysis)
#         # Test if the files are created with the right content
#