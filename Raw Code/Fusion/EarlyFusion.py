#!/usr/bin/env python
# -*- encoding: utf-8

import numpy as np

# TODO :
# Linear Weighted Fusion
# Bayesian Inference  /!\ Statistically independant => ? 
# Dempster Schafer Theory  /!\ Inunderstandable
# Dynamic Bayesian Networks
# Neural Network
# Maximum Entropy Model
# Kalman Filter
# Particle Filter

def linearWeightedFusion (toFuse, weights):
	
	# Normalize weights ?
	# weights = weights/float(max(weights))

	fused = np.array([component*weights for (component, weight) in zip(toFuse, weights)])
	
	return fused


