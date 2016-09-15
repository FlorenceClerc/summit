from scipy import sparse
import numpy as np


def getV(DATASET, viewIndex, usedIndices=None):
    if usedIndices==None:
        usedIndices = range(DATASET.get("Metadata").attrs["datasetLength"])
    if not DATASET.get("View"+str(viewIndex)).attrs["sparse"]:
        return DATASET.get("View"+str(viewIndex))[usedIndices, :]
    else:
        return sparse.csr_matrix((DATASET.get("View"+str(viewIndex)).get("data").value,
                                  DATASET.get("View"+str(viewIndex)).get("indices").value,
                                  DATASET.get("View"+str(viewIndex)).get("indptr").value),
                                 shape=DATASET.get("View"+str(viewIndex)).attrs["shape"])[usedIndices,:]


def getShape(DATASET, viewIndex):
    if not DATASET.get("View"+str(viewIndex)).attrs["sparse"]:
        return DATASET.get("View"+str(viewIndex)).shape
    else:
        return DATASET.get("View"+str(viewIndex)).attrs["shape"]


def getValue(DATASET):
    if not DATASET.attrs["sparse"]:
        return DATASET.value
    else:
        return sparse.csr_matrix((DATASET.get("data").value,
                                  DATASET.get("indices").value,
                                  DATASET.get("indptr").value),
                                 shape=DATASET.attrs["shape"])

def extractSubset(matrix, usedIndices):
    if sparse.issparse(matrix):
        newIndptr = np.zeros(len(usedIndices)+1, dtype=np.int16)
        oldindptr = matrix.indptr
        for exampleIndexIndex, exampleIndex in enumerate(usedIndices):
            if exampleIndexIndex>0:
                newIndptr[exampleIndexIndex] = newIndptr[exampleIndexIndex-1]+(oldindptr[exampleIndex]-oldindptr[exampleIndex-1])
        newData = np.ones(newIndptr[-1], dtype=bool)
        newIndices =  np.zeros(newIndptr[-1], dtype=np.int32)
        oldIndices = matrix.indices
        for exampleIndexIndex, exampleIndex in enumerate(usedIndices):
            newIndices[newIndptr[exampleIndexIndex]:newIndptr[exampleIndexIndex+1]] = oldIndices[oldindptr[exampleIndex]: oldindptr[exampleIndex+1]]
        return sparse.csr_matrix((newData, newIndices, newIndptr), shape=(len(usedIndices), matrix.shape))
    else:
        return matrix[usedIndices]