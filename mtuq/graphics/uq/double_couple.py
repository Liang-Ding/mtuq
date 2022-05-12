#
# graphics/uq/double_couple.py - uncertainty quantification of double couple sources
#

import numpy as np

from matplotlib import pyplot
from pandas import DataFrame
from xarray import DataArray
from mtuq.graphics._gmt import read_cpt, _cpt_path
from mtuq.graphics.uq._matplotlib import _plot_dc_matplotlib
from mtuq.grid_search import MTUQDataArray, MTUQDataFrame
from mtuq.util import dataarray_idxmin, dataarray_idxmax, fullpath, warn
from mtuq.util.math import closed_interval, open_interval, to_delta, to_gamma, to_mij
from os.path import exists


def plot_misfit_dc(filename, ds, **kwargs):
    """ Plots misfit values over strike, dip, slip

    .. rubric :: Required input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    Data structure containing moment tensors and corresponding misfit values


    .. rubric :: Optional input arguments

    For optional argument descriptions, 
    `see here <mtuq.graphics._plot_dc.html>`_

    """
    _defaults(kwargs, {
        'colormap': 'viridis',
        'type_best': 'min',
        })

    _check(ds)

    if issubclass(type(ds), DataArray):
        misfit = _misfit_dc_regular(ds)
        
    elif issubclass(type(ds), DataFrame):
        warn('plot_misfit_dc not implemented for irregularly-spaced grids.\n'
             'No figure will be generated.')
        return

    _plot_dc(filename, misfit, **kwargs)



def plot_likelihood_dc(filename, ds, var, **kwargs):
    """ Plots maximum likelihood values over strike, dip, slip

    .. rubric :: Required input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    Data structure containing moment tensors and corresponding misfit values

   ``var`` (`float` or `array`):
    Data variance


    .. rubric :: Optional input arguments

    For optional argument descriptions, 
    `see here <mtuq.graphics._plot_dc.html>`_

    """
    _defaults(kwargs, {
        'colormap': 'hot_r',
        'type_best': 'max',
        })

    _check(ds)

    if issubclass(type(ds), DataArray):
        likelihoods = _likelihoods_dc_regular(ds, var)

    elif issubclass(type(ds), DataFrame):
        warn('plot_misfit_dc not implemented for irregularly-spaced grids. '
             'No figure will be generated.')
        return

    _plot_dc(filename, likelihoods, **kwargs)



def plot_marginal_dc():
    raise NotImplementedError



def plot_variance_reduction_dc(filename, ds, data_norm, **kwargs):
    """ Plots variance reduction values over strike, dip, slip

    .. rubric :: Required input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    Data structure containing moment tensors and corresponding misfit values

   ``data_norm`` (`float`):
    Data norm


    .. rubric :: Optional input arguments

    For optional argument descriptions, 
    `see here <mtuq.graphics._plot_dc.html>`_

    """
    _defaults(kwargs, {
        'colormap': 'viridis',
        'type_best': 'max',
        })

    _check(ds)

    if issubclass(type(ds), DataArray):
        variance_reduction = _variance_reduction_dc_regular(ds, var)

    elif issubclass(type(ds), DataFrame):
        warn('plot_misfit_dc not implemented for irregularly-spaced grids. '
             'No figure will be generated.')
        return

    _plot_dc(filename, variance_reduction, **kwargs)



def _plot_dc(filename, da, show_best=True, colormap='hot', 
    backend=_plot_dc_matplotlib, type_best='min', **kwargs):

    """ Plots DataArray values over strike, dip, slip

    .. rubric :: Keyword arguments

    ``colormap`` (`str`)
    Color palette used for plotting values 
    (choose from GMT or MTUQ built-ins)

    ``show_best`` (`bool`):
    Show where best-fitting orientation falls on strike, dip, slip plots

    ``title`` (`str`)
    Optional figure title

    ``backend`` (`function`)
    Choose from `_plot_dc_matplotlib` (default) or user-supplied function

    """

    if not issubclass(type(da), DataArray):
        raise Exception()

    if show_best:
        if 'best_dc' in da.attrs:
            best_dc = da.attrs['best_dc']
        else:
            warn("Best-fitting orientation not given")
            best_dc = None

    # collect values
    if type_best=='min':
        values_h_kappa = da.min(dim=('sigma')).values
        values_sigma_kappa = da.min(dim=('h')).values
        values_sigma_h= da.min(dim=('kappa')).values.T
    elif type_best=='max':
        values_h_kappa = da.max(dim=('sigma')).values
        values_sigma_kappa = da.max(dim=('h')).values
        values_sigma_h= da.max(dim=('kappa')).values.T
    else:
        raise ValueError

    backend(filename,
        da.coords,
        values_h_kappa,
        values_sigma_kappa,
        values_sigma_h,
        best_dc=best_dc,
        **kwargs)


#
# for extracting misfit, variance reduction and likelihood from
# regularly-spaced grids
#

def _misfit_dc_regular(da):
    """ For each moment tensor orientation, extract minimum misfit
    """
    misfit = da.min(dim=('origin_idx', 'rho', 'v', 'w'))

    return misfit.assign_attrs({
        'best_mt': _min_mt(da),
        'best_dc': _min_dc(da),
        })


def _likelihoods_dc_regular(da, var):
    """ For each moment tensor orientation, calculate maximum likelihood
    """
    likelihoods = da.copy()
    likelihoods.values = np.exp(-likelihoods.values/(2.*var))
    likelihoods.values /= likelihoods.values.sum()

    likelihoods = likelihoods.max(dim=('origin_idx', 'rho', 'v', 'w'))
    likelihoods.values /= likelihoods.values.sum()
    #likelihoods /= dc_area

    return likelihoods.assign_attrs({
        'best_mt': _min_mt(da),
        'best_dc': _min_dc(da),
        'maximum_likelihood_estimate': dataarray_idxmax(likelihoods).values(),
        })


def _marginals_dc_regular(da, var):
    """ For each moment tensor orientation, calculate marginal likelihood
    """
    raise NotImplementedError


def _variance_reduction_dc_regular(da, data_norm):
    """ For each source type, extracts maximum variance reduction
    """
    variance_reduction = 1. - da.copy()/data_norm

    variance_reduction = variance_reduction.max(
        dim=('origin_idx', 'rho', 'v', 'w'))

    # in geophysics, variance reduction is usually given as a percentage
    variance_reduction.values *= 100.

    return variance_reduction.assign_attrs({
        'best_mt': _min_mt(da),
        'best_dc': _min_dc(da),
        'lune_array': _lune_array(da),
        })


#
# utility functions
#

def _min_mt(da):
    """ Returns moment tensor vector corresponding to mininum DataArray value
    """
    da = dataarray_idxmin(da)
    lune_keys = ['rho', 'v', 'w', 'kappa', 'sigma', 'h']
    lune_vals = [da[key].values for key in lune_keys]
    return to_mij(*lune_vals)


def _max_mt(da):
    """ Returns moment tensor vector corresponding to maximum DataArray value
    """
    da = dataarray_idxmax(da)
    lune_keys = ['rho', 'v', 'w', 'kappa', 'sigma', 'h']
    lune_vals = [da[key].values for key in lune_keys]
    return to_mij(*lune_vals)


def _min_dc(da):
    """ Returns orientation angles corresponding to mininum DataArray value
    """
    da = dataarray_idxmin(da)
    dc_keys = ['kappa', 'sigma', 'h']
    dc_vals = [da[key].values for key in dc_keys]
    return dc_vals

def _max_dc(da):
    """ Returns orientation angles corresponding to maximum DataArray value
    """
    da = dataarray_idxmax(da)
    dc_keys = ['kappa', 'sigma', 'h']
    dc_vals = [da[key].values for key in dc_keys]
    return dc_vals



def _check(ds):
    """ Checks data structures
    """
    if type(ds) not in (DataArray, DataFrame, MTUQDataArray, MTUQDataFrame):
        raise TypeError("Unexpected grid format")


def _defaults(kwargs, defaults):
    for key in defaults:
        if key not in kwargs:
           kwargs[key] = defaults[key]

