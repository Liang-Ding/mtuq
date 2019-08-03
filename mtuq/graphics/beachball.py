#
# utilities for plotting
#

import numpy as np
import matplotlib.pyplot as pyplot
from mtuq.event import MomentTensor
from mtuq.graphics.waveform import _hide_axes
from obspy.imaging.beachball import beach, beachball



def plot_beachball(filename, mt):
    """ Plots source mechanism
    """
    beachball(mt, size=200, linewidth=2, facecolor='b')
    pyplot.savefig(filename)


def misfit_vs_depth(filename, results, origins, mt):
    """ Plots misfit versus depth from grid search results

    Creates a scatter plot in which the the placment of each marker shows the 
    misfit of the best-fitting source for a given depth. 

    Following SilwalTape2016, the marker itself shows the focal mechanism and
    moment magnitude of the best-fitting source.
    """

    nn=len(origins)
    fig = pyplot.figure(figsize=(nn+1, 1))
    ax = pyplot.gca()

    for _i, origin in enumerate(origins):
        best_misfit = results[_i, :].min()
        best_mt = sources.get(results[_i, :].argmin())

        # add beachball
        ax.add_collection(
            beach(best_mt, xy=(_i+1, 0.125), width=0.5))

        # add depth label
        label = '%d km' % (origin.depth_in_m/1000.)
        x, y = _i+1, -0.5

        pyplot.text(x, y, label,
            fontsize=8,
            horizontalalignment='center')

        # add magnitude label
        label = '%2.1f' % MomentTensor(best_mt).magnitude()
        x, y = _i+1, -0.33

        pyplot.text(x, y, label,
            fontsize=8,
            horizontalalignment='center')

    ax.set_aspect("equal")
    ax.set_xlim((0, nn+1))
    ax.set_ylim((-0.5, +0.5))
    _hide_axes(ax)

    pyplot.savefig(filename)
    pyplot.close()

