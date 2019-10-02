import numpy as np

from multiview_platform.mono_multi_view_classifiers.multiview_classifiers.additions.diversity_utils import \
    CoupleDiversityFusion

classifier_class_name = "DoubleFaultFusion"


class DoubleFaultFusion(CoupleDiversityFusion):

    def diversity_measure(self, first_classifier_decision,
                          second_classifier_decision, y):
        return np.logical_and(np.logical_xor(first_classifier_decision, y),
                              np.logical_xor(second_classifier_decision, y))