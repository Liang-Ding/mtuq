#
# graphics/uq_dc.py - uncertainty quantification of double couple sources
#

import numpy as np
import warnings

from matplotlib import pyplot
from pandas import DataFrame
from xarray import DataArray
from mtuq.util.lune import to_delta, to_gamma
from mtuq.util.math import closed_interval, open_interval


def plot_misfit_dc(filename, ds):
    """ Plots misfit over strike, dip, and slip
    (matplotlib implementation)
    """
    ds = ds.copy()

    if issubclass(type(ds), DataArray):
        _plot_dc(filename, _marginal(ds))
        
    elif issubclass(type(ds), DataFrame):
        warnings.warn(
            'plot_misfit_dc not implemented for irregularly-spaced grids')


def _marginal(da):
    if 'origin_idx' in da.dims:
        da = da.max(dim='origin_idx')

    if 'rho' in da.dims:
        da = da.max(dim='rho')

    if 'v' in da.dims:
        assert len(da.coords['v'])==1
        da = da.squeeze(dim='v')

    if 'w' in da.dims:
        assert len(da.coords['w'])==1
        da = da.squeeze(dim='w')

    return da



def _plot_dc(filename, da):
    # prepare axes
    fig, axes = pyplot.subplots(2, 2, 
        figsize=(8., 6.),
        )

    pyplot.subplots_adjust(
        wspace=0.33,
        hspace=0.33,
        )

    kwargs = {
        'cmap': 'plasma',
        }

    axes[1][0].axis('off')


    # FIXME: do labels correspond to the correct axes ?!
    marginal = da.min(dim=('sigma'))
    x = marginal.coords['h']
    y = marginal.coords['kappa']
    pyplot.subplot(2, 2, 1)
    pyplot.pcolor(x, y, marginal.values, **kwargs)
    pyplot.xlabel('cos(dip)')
    pyplot.ylabel('strike')

    marginal = da.min(dim=('h'))
    x = marginal.coords['sigma']
    y = marginal.coords['kappa']
    pyplot.subplot(2, 2, 2)
    pyplot.pcolor(x, y, marginal.values, **kwargs)
    pyplot.xlabel('slip')
    pyplot.ylabel('strike')

    marginal = da.min(dim=('kappa'))
    x = marginal.coords['sigma']
    y = marginal.coords['h']
    pyplot.subplot(2, 2, 4)
    pyplot.pcolor(x, y, marginal.values.T, **kwargs)
    pyplot.xlabel('slip')
    pyplot.ylabel('cos(dip)')

    pyplot.savefig(filename)


