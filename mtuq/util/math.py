
import numpy as np
from scipy.signal import fftconvolve


def list_intersect(a, b):
    """ Intersection of two lists
    """
    return list(set(a).intersection(set(b)))


def list_intersect_with_indices(a, b):
    intersection = list(set(a).intersection(set(b)))
    indices = [a.index(item) for item in intersection]
    return intersection, indices


def isclose(X, Y):
    EPSVAL = 1.e-6
    X = np.array(X)
    Y = np.array(Y)
    return bool(
        np.linalg.norm(X-Y) < EPSVAL)


def open_interval(x1,x2,nx):
    return np.linspace(x1,x2,2*nx+1)[1:-1:2]


def closed_interval(x1,x2,nx):
    return np.linspace(x1,x2,nx)


def tight_interval(x1,x2,nx,tightness=0.999):
    # tightness (float) 
    # 0. reduces to ``open_intervel``, 1. reduces to ``closed_intervel``
    Lo = open_interval(x1,x2,nx)
    Lc = closed_interval(x1,x2,nx)
    return Lo*(1.-tightness) + Lc*tightness


def correlate(v1, v2):
    """ Fast cross-correlation function

    Correlates unpadded array v1 and padded array v2, producing result of 
    shape ``len(v2) - len(v1)``
    """
    n1, n2 = len(v1), len(v2)

    if n1>2000 or n2-n1>200:
        # for long traces, frequency-domain implementation is usually faster
        return fftconvolve(v1, v2[::-1], 'valid')
    else:
        # for short traces, time-domain implementation is usually faster
        return np.correlate(v1, v2, 'valid')



