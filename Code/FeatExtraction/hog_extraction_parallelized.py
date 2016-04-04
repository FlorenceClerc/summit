#!/usr/bin/env python

""" Library: Caclulates the HOG Feature - parallelized """

# Import built-in modules
import os as os                                 # for iteration throug directories
import datetime                                 # for TimeStamp in CSVFile
import time                                     # for time calculations

# Import 3rd party modules
import numpy as np                              # for arrays
import pandas as pd                             # for Series and DataFrames
import cv2                                      # for OpenCV
from skimage.feature import hog
from sklearn.cluster import MiniBatchKMeans
import multiprocessing as mp                    #to count cores https://docs.python.org/3/library/multiprocessing.html#multiprocessing.pool.Pool
from joblib import Parallel, delayed
import logging                                  # To create Log-Files  

# Import own modules
import DBCrawl

# Author-Info
__author__ 	= "Baptiste Bauvin and co-author Nikolas Huelsmann"
__status__ 	= "?"                           # Production, Development, Prototype
__date__	= "?"


# In order to calculate HOG, we will use a bag of word approach : cf SURF function, well documented. 

def reSize(image, CELL_DIMENSION):
  height, width, channels = image.shape
  
  if height%CELL_DIMENSION==0 and width%CELL_DIMENSION==0:
    resizedImage = image
  
  elif width%CELL_DIMENSION==0:
    missingPixels = CELL_DIMENSION-height%CELL_DIMENSION
    resizedImage = cv2.copyMakeBorder(image,0,missingPixels,0,\
                                      0,cv2.BORDER_REPLICATE)
  
  elif height%CELL_DIMENSION==0:
    missingPixels = CELL_DIMENSION-width%CELL_DIMENSION
    resizedImage = cv2.copyMakeBorder(image,0,0,0,missingPixels,\
                                      cv2.BORDER_REPLICATE)
  
  else:
    missingWidthPixels = CELL_DIMENSION-width%CELL_DIMENSION
    missingHeightPixels = CELL_DIMENSION-height%CELL_DIMENSION
    resizedImage = cv2.copyMakeBorder(image,0,missingHeightPixels,0,\
                                      missingWidthPixels,cv2.BORDER_REPLICATE)
  return resizedImage


def imageSequencing(npImage, CELL_DIMENSION):
  image = cv2.imread(npImage[1])
  resizedImage = reSize(image, CELL_DIMENSION)
  height, width, channels = resizedImage.shape
  cells = np.array([\
      resizedImage[\
        j*CELL_DIMENSION:j*CELL_DIMENSION+CELL_DIMENSION,\
        i*CELL_DIMENSION:i*CELL_DIMENSION+CELL_DIMENSION] \
      for i in range(width/CELL_DIMENSION) \
      for j in range(height/CELL_DIMENSION)\
    ])
  return np.array(cells)  


def corpusSequencing(npImages, CELL_DIMENSION, NB_CORES):
  corpusCells = Parallel(n_jobs=NB_CORES)\
                (delayed(imageSequencing)(image, CELL_DIMENSION) \
                for image in npImages)

  corpusCells = np.array(corpusCells)
  return corpusCells


def computeLocalHistogramsImage(image, NB_ORIENTATIONS, CELL_DIMENSION):
  nbCells = len(image)
  localHistograms = ["histo" for j in range(nbCells)]
  for j in range(nbCells):
    localHistograms[j] = hog(cv2.cvtColor(image[j], cv2.COLOR_BGR2GRAY), \
                            orientations=NB_ORIENTATIONS, \
                            pixels_per_cell=(CELL_DIMENSION,\
                                            CELL_DIMENSION),\
                            cells_per_block=(1,1)) 
  return np.array(localHistograms)


def computeLocalHistograms(images, NB_ORIENTATIONS, CELL_DIMENSION, NB_CORES):
  localHistograms = Parallel(n_jobs=NB_CORES)\
                (delayed(computeLocalHistogramsImage)(image, NB_ORIENTATIONS, CELL_DIMENSION) \
                for image in images)

  return np.array(localHistograms)


def clusterGradients(localHistograms, NB_CLUSTERS, MAXITER):
  sizes = np.array([len(localHistogram) for localHistogram in localHistograms])
  nbImages =  len(localHistograms)
  flattenedHogs = np.array([cell for image in localHistograms for cell in image])
  miniBatchKMeans = MiniBatchKMeans(n_clusters=NB_CLUSTERS, max_iter=MAXITER, \
                    compute_labels=True)
  localHistogramLabels = miniBatchKMeans.fit_predict(flattenedHogs)
  return localHistogramLabels, sizes


def makeHistograms(labels, NB_CLUSTERS, sizes):
  indiceInLabels = 0
  hogs = []
  for image in sizes:
    histogram = np.zeros(NB_CLUSTERS)
    for i in range(image):
      histogram[labels[indiceInLabels+i]] += 1.0
    hogs.append(histogram/image)
    indiceInLabels+=i 
  return np.array(hogs)


def extractHOGFeatureParallel(npImages, CELL_DIMENSION, NB_ORIENTATIONS, \
                      NB_CLUSTERS, MAXITER, NB_CORES):
  cells = corpusSequencing(npImages, CELL_DIMENSION, NB_CORES)
  localHistograms = computeLocalHistograms(cells, NB_ORIENTATIONS, CELL_DIMENSION, NB_CORES)
  localHistogramLabels, sizes = clusterGradients(localHistograms, \
                                                NB_CLUSTERS, MAXITER)
  hogs = makeHistograms(localHistogramLabels, NB_CLUSTERS, sizes)
  return hogs


# Main for testing
if __name__ == '__main__':


  start = time.time()
  # path='/home/doob/Dropbox/Marseille/OMIS-Projet/03-jeux-de-donnees/101_ObjectCategories'
  path ='/donnees/pj_bdd_bbauvin/101_ObjectCategories'
  testNpImages = [ [1,'testImage.jpg'], [1,'testImage.jpg'] ]
  CELL_DIMENSION = 5
  NB_ORIENTATIONS = 8
  NB_CLUSTERS = 12
  MAXITER = 100
  NB_CORES = mp.cpu_count()

  logging.debug("Fetching Images in " + path)
  # get dictionary to link classLabels Text to Integers
  sClassLabels = getClassLabels(path)
  # # Get all path from all images inclusive classLabel as Integer
  dfImages = imgCrawl(path, sClassLabels)
  npImages = dfImages.values
  extractedTime = time.time()
  logging.debug("Extracted images in " + str(extractedTime-start) +'sec')
  logging.debug("Sequencing Images ...")
  cells = corpusSequencing(npImages, CELL_DIMENSION, NB_CORES)
  sequencedTime = time.time()
  logging.debug("Sequenced images in " + str(sequencedTime-extractedTime) +'sec')
  logging.debug("Computing gradient on each block ...")
  gradients = computeLocalHistograms(cells, NB_ORIENTATIONS, CELL_DIMENSION, NB_CORES)
  hogedTime = time.time()
  logging.debug("Computed gradients in " + str(hogedTime - sequencedTime) + 'sec')
  logging.debug("Clustering gradients ...")
  gradientLabels, sizes = clusterGradients(gradients, NB_CLUSTERS, MAXITER)
  clusteredItme = time.time()
  logging.debug("Clustered gradients in " + str(hogedTime - sequencedTime) + 'sec')
  logging.debug("Computing histograms ...")
  histograms = makeHistograms(gradientLabels, NB_CLUSTERS, sizes)
  end = time.time()
  logging.debug("Computed histograms in " + str(int(end - hogedTime)) + 'sec')
  logging.debug("Histogram shape : " +str(histograms.shape))
  logging.debug("Total time : " + str(end-start) + 'sec')
  #hogs = extractHOGFeature(testNpImages, CELL_DIMENSION, \
  #                         NB_ORIENTATIONS, NB_CLUSTERS, MAXITER)
  