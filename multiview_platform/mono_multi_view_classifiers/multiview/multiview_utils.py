from sklearn.base import BaseEstimator, ClassifierMixin
import numpy as np

from .. import multiview_classifiers



class MultiviewResult(object):
    def __init__(self, classifier_name, classifier_config,
                 metrics_scores, full_labels, test_labels_multiclass):
        self.classifier_name = classifier_name
        self.classifier_config = classifier_config
        self.metrics_scores = metrics_scores
        self.full_labels_pred = full_labels
        self.y_test_multiclass_pred = test_labels_multiclass

    def get_classifier_name(self):
        multiview_classifier_module = getattr(multiview_classifiers,
                                            self.classifier_name)
        multiview_classifier = getattr(multiview_classifier_module,
                                       multiview_classifier_module.classifier_class_name)()
        return multiview_classifier.short_name


def get_names(classed_list):
    return np.array([object_.__class__.__name__ for object_ in classed_list])


class BaseMultiviewClassifier(BaseEstimator, ClassifierMixin):

    def __init__(self, random_state):
        self.random_state = random_state
        self.short_name = self.__class__.__name__

    def genBestParams(self, detector):
        return dict((param_name, detector.best_params_[param_name])
                    for param_name in self.param_names)

    def genParamsFromDetector(self, detector):
        if self.classed_params:
            classed_dict = dict((classed_param, get_names(
                detector.cv_results_["param_" + classed_param]))
                                for classed_param in self.classed_params)
        if self.param_names:
            return [(param_name,
                     np.array(detector.cv_results_["param_" + param_name]))
                    if param_name not in self.classed_params else (
                param_name, classed_dict[param_name])
                    for param_name in self.param_names]
        else:
            return [()]

    def genDistribs(self):
        return dict((param_name, distrib) for param_name, distrib in
                    zip(self.param_names, self.distribs))

    def params_to_string(self):
        return ", ".join(
                [param_name + " : " + self.to_str(param_name) for param_name in
                 self.param_names])

    def getConfig(self):
        if self.param_names:
            return "\n\t\t- " + self.__class__.__name__ + "with " + self.params_to_string()
        else:
            return "\n\t\t- " + self.__class__.__name__ + "with no config."

    def to_str(self, param_name):
        if param_name in self.weird_strings:
            string = ""
            if "class_name" in self.weird_strings[param_name] :
                string+=self.get_params()[param_name].__class__.__name__
            if "config" in self.weird_strings[param_name]:
                string += "( with "+ self.get_params()[param_name].params_to_string()+")"
            else:
                string+=self.weird_strings[param_name](
                    self.get_params()[param_name])
            return string
        else:
            return str(self.get_params()[param_name])

    def get_interpretation(self):
        return "No detailed interpretation function"




def get_train_views_indices(dataset, train_indices, view_indices,):
    """This function  is used to get all the examples indices and view indices if needed"""
    if view_indices is None:
        view_indices = np.arange(dataset["Metadata"].attrs["nbView"])
    if train_indices is None:
        train_indices = range(dataset["Metadata"].attrs["datasetLength"])
    return train_indices, view_indices