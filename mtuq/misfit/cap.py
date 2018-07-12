
from collections import defaultdict
from math import ceil, floor
from scipy.signal import fftconvolve
from mtuq.util.math import isclose
import numpy as np
import warnings


class Misfit(object):
    """ 
    CAP-style data misfit function

    Evaluating misfit is a two-step procedure:
        1) function_handle = cap_misfit(**parameters)
        2) misfit = function_handle(data, synthetics)

    In the first step, the user supplies a list of parameters, including
    the order of the norm applied to the residuals, whether or not to use
    polarity information, and various tuning parameters (see below for detailed
    descriptions.) In the second step, the user supplies data and synthetics 
    and gets back the corresponding misfit value.
    """

    def __init__(self,
        norm_order=1,
        polarity_weight=0.,
        time_shift_groups=['ZRT'],
        time_shift_max=0.,
        ):
        """ Checks misfit parameters

        time_shift_groups
            ['ZRT'] locks time-shift across all three components
            ['ZR','T'] locks vertical and radial components only
            ['Z','R','T'] allows time shifts to vary freely between components

        """
        for group in time_shift_groups:
            for component in group:
                assert component in ['Z','R','T']

        # what norm should we apply to the residuals?
        self.order = norm_order

        # maximum cross-correlation lag (seconds)
        self.time_shift_max = time_shift_max

        # should we allow time shifts to vary from component to component?
        self.time_shift_groups = time_shift_groups

        # should we include polarities in misfit?
        self.polarity_weight = polarity_weight


    def __call__(self, data, greens, mt):
        """ CAP-style misfit calculation
        """ 
        p = self.order
        synthetics = greens.get_synthetics(mt)

        sum_misfit = 0.
        for d, s in zip(data, synthetics):
            # time sampling scheme
            npts = d[0].data.size
            dt = d[0].stats.delta


            #
            # PART 1: Prepare for time-shift correction
            #

            npts_dat = npts
            npts_syn = s[0].data.size
            npts_padding = int(round(self.time_shift_max/dt))

            if npts_syn - npts_dat == 2*npts_padding:
                # synthetics have already been padded, nothing to do just yet
                pass

            elif npts_dat == npts_syn:
               warnings.warn("For greater speed, pad synthetics in advance by "
                   "by setting process_data.padding_length equal to "
                   "misfit.time_shift_max")
               for trace in s:
                   trace.data = np.pad(trace.data, npts_padding, 'constant')

            else:
               raise Exception("Data and synthetics must be the same "
                   "length, or synthetics padded by a number of samples "
                   "equal to 2*time_shift_max/dt")

            if not hasattr(d, 'time_shift_mode'):
                # Chooses whether to work in the time or frequency domain based 
                # on length of traces and maximum allowable lag
                if npts_padding==0:
                    d.time_shift_mode = 0
                elif npts > 2000 or npts_padding > 200:
                    # for long traces or long lag times, frequency-domain
                    # implementation is usually faster
                    d.time_shift_mode = 1
                else:
                    # for short traces or short lag times, time-domain
                    # implementation is usually faster
                    d.time_shift_mode = 2


            #
            # PART 2: CAP-style waveform-difference misfit calculation, with
            #     time-shift corrections
            #
             
            for group in self.time_shift_groups:
                # Finds the time-shift between data and synthetics that yields
                # the maximum cross-correlation value across all components in 
                # in a given group, subject to time_shift_max constraint

                result = np.zeros(2*npts_padding+1)
                _indices = []
                for _i in range(len(d)):
                    # ignore traces with zero misfit weight
                    if hasattr(d[_i], 'weight') and d[_i].weight == 0.:
                        continue

                    # keep track of which indices correspond to which components
                    component = d[_i].stats.channel[-1].upper()
                    if component in group:
                        _indices += [_i]
                    else:
                        continue

                    if d.time_shift_mode==0:
                        pass
                    elif d.time_shift_mode==1:
                        result += fftconvolve(
                            d[_i].data, s[_i].data[::-1], 'valid')
                    elif d.time_shift_mode==2:
                        result += np.correlate(
                            d[_i].data, s[_i].data, 'valid')

                # what time-shift yields the maximum cross-correlation value?
                argmax = result.argmax()
                time_shift = (argmax-npts_padding)*dt

                # what start and stop indices will correctly shift synthetics 
                # relative to data?
                start = 2*npts_padding-argmax
                stop = 2*npts_padding-argmax+npts

                for _i in _indices:
                    s[_i].time_shift = time_shift
                    s[_i].time_shift_group = group
                    s[_i].start = start
                    s[_i].stop = stop
                    
                    # substract data from shifted synthetics
                    r = s[_i].data[start:stop] - d[_i].data

                    # sum the resulting residuals
                    d[_i].sum_residuals = np.sum(np.abs(r)**p)*dt
                    sum_misfit += d[_i].weight * d[_i].sum_residuals



            #
            # PART 3: CAP-style polarity calculation
            #

            if self.polarity_weight > 0.:
                raise NotImplementedError


        return sum_misfit**(1./p)


