import numpy as np

from ..multiview_classifiers.additions.late_fusion_utils import LateFusionClassifier
from ..utils.dataset import get_examples_views_indices

classifier_class_name = "WeightedLinearLateFusion"


class WeightedLinearLateFusion(LateFusionClassifier):
    def __init__(self, random_state, classifiers_names=None,
                 classifier_configs=None, weights=None, nb_cores=1, rs=None):
        self.need_probas=True
        super(WeightedLinearLateFusion, self).__init__(random_state=random_state,
                                      classifiers_names=classifiers_names,
                                      classifier_configs=classifier_configs,
                                      nb_cores=nb_cores,weights=weights, rs=rs)

    def predict(self, X, example_indices=None, view_indices=None):
        example_indices, views_indices = get_examples_views_indices(X, example_indices, view_indices)
        view_scores = []
        for index, viewIndex in enumerate(views_indices):
            view_scores.append(np.array(self.monoview_estimators[index].predict_proba(
                X.get_v(viewIndex, example_indices))) * self.weights[index])
        view_scores = np.array(view_scores)
        predicted_labels = np.argmax(np.sum(view_scores, axis=0), axis=1)
        return predicted_labels
