#!/usr/bin/env python

import os
import numpy as np

from mtuq import read, open_db, download_greens_tensors
from mtuq.event import Origin
from mtuq.graphics import plot_data_greens2, plot_beachball, plot_misfit_lune
from mtuq.grid import FullMomentTensorGridSemiregular
from mtuq.grid_search import grid_search
from mtuq.misfit import Misfit
from mtuq.process_data import ProcessData
from mtuq.util import fullpath, save_json
from mtuq.util.cap import parse_station_codes, Trapezoid



if __name__=='__main__':
    #
    # Carries out grid search over all moment tensor parameters except
    # magnitude 
    #
    # USAGE
    #   mpirun -n <NPROC> python GridSearch.FullMomentTensor.py
    #   


    path_data=    fullpath('data/examples/20090407201255351/*.[zrt]')
    path_weights= fullpath('data/examples/20090407201255351/weights.dat')
    event_id=     '20090407201255351'
    model=        'ak135'


    #
    # Body and surface wave measurements will be made separately
    #

    process_bw = ProcessData(
        filter_type='Bandpass',
        freq_min= 0.1,
        freq_max= 0.333,
        pick_type='taup',
        taup_model=model,
        window_type='body_wave',
        window_length=15.,
        capuaf_file=path_weights,
        )

    process_sw = ProcessData(
        filter_type='Bandpass',
        freq_min=0.025,
        freq_max=0.0625,
        pick_type='taup',
        taup_model=model,
        window_type='surface_wave',
        window_length=150.,
        capuaf_file=path_weights,
        )


    #
    # For our objective function, we will use a sum of body and surface wave
    # contributions
    #

    misfit_bw = Misfit(
        norm='L2',
        time_shift_min=-2.,
        time_shift_max=+2.,
        time_shift_groups=['ZR'],
        )

    misfit_sw = Misfit(
        norm='L2',
        time_shift_min=-10.,
        time_shift_max=+10.,
        time_shift_groups=['ZR','T'],
        )


    #
    # User-supplied weights control how much each station contributes to the
    # objective function
    #

    station_id_list = parse_station_codes(path_weights)


    #
    # Next, we specify the moment tensor grid and source-time function
    #

    grid = FullMomentTensorGridSemiregular(
        npts_per_axis=15,
        magnitudes=[4.5])

    wavelet = Trapezoid(
        magnitude=4.5)


    #
    # Origin time and location will be fixed. For an example in which they 
    # vary, see examples/GridSearch.DoubleCouple+Magnitude+Depth.py
    #
    # See also Dataset.get_origins(), which attempts to create Origin objects
    # from waveform metadata
    #

    origin = Origin({
        'time': '2009-04-07T20:12:55.000000Z',
        'latitude': 61.454200744628906,
        'longitude': -149.7427978515625,
        'depth_in_m': 33033.599853515625,
        'id': '20090407201255351'
        })


    from mpi4py import MPI
    comm = MPI.COMM_WORLD


    #
    # The main I/O work starts now
    #

    if comm.rank==0:
        print('Reading data...\n')
        data = read(path_data, format='sac', 
            event_id=event_id,
            station_id_list=station_id_list,
            tags=['units:cm', 'type:velocity']) 


        data.sort_by_distance()
        stations = data.get_stations()


        print('Processing data...\n')
        data_bw = data.map(process_bw)
        data_sw = data.map(process_sw)


        print('Reading Greens functions...\n')
        greens = download_greens_tensors(stations, origin, model)

        print('Processing Greens functions...\n')
        greens.convolve(wavelet)
        greens_bw = greens.map(process_bw)
        greens_sw = greens.map(process_sw)


    else:
        stations = None
        data_bw = None
        data_sw = None
        greens_bw = None
        greens_sw = None


    stations = comm.bcast(stations, root=0)
    data_bw = comm.bcast(data_bw, root=0)
    data_sw = comm.bcast(data_sw, root=0)
    greens_bw = comm.bcast(greens_bw, root=0)
    greens_sw = comm.bcast(greens_sw, root=0)


    #
    # The main computational work starts now
    #

    if comm.rank==0:
        print('Evaluating body wave misfit...\n')

    results_bw = grid_search(
        data_bw, greens_bw, misfit_bw, origin, grid)

    if comm.rank==0:
        print('Evaluating surface wave misfit...\n')

    results_sw = grid_search(
        data_sw, greens_sw, misfit_sw, origin, grid)


    #
    # Analyzing results
    #

    if comm.rank==0:

        results = results_bw + results_sw

        # source corresponding to minimum misfit
        idx = results.idxmin('source')
        best_source = grid.get(idx)
        lune_dict = grid.get_dict(idx)
        mt_dict = grid.get(idx).as_dict()

        components_bw = data_bw.get_components()
        components_sw = data_sw.get_components()

        # synthetics corresponding to minimum misfit
        synthetics_bw = greens_bw.get_synthetics(
            best_source, components_bw, mode='map')

        synthetics_sw = greens_sw.get_synthetics(
            best_source, components_sw, mode='map')

        # time shifts corresponding to minimum misfit
        attrs_bw = misfit_bw.collect_attributes(
            data_bw, greens_bw, best_source)

        attrs_sw = misfit_sw.collect_attributes(
            data_sw, greens_sw, best_source)


        print('Generating figures...\n')

        plot_data_greens2(event_id+'FMT_waveforms.png',
            data_bw, data_sw, greens_bw, greens_sw, process_bw, process_sw, 
            misfit_bw, misfit_sw, stations, origin, best_source, lune_dict)

        plot_beachball(event_id+'FMT_beachball.png', best_source)

        plot_misfit_lune(event_id+'DC_misfit.png', results)


        print('Saving results...\n')

        os.makedirs(event_id+'FMT/waveforms/data', exist_ok=True)
        os.makedirs(event_id+'FMT/waveforms/synthetics', exist_ok=True)

        os.makedirs(event_id+'FMT/misfit/bw', exist_ok=True)
        os.makedirs(event_id+'FMT/misfit/sw', exist_ok=True)

        save_json(event_id+'FMT_mt.json', mt_dict)
        save_json(event_id+'FMT_lune.json', lune_dict)

        data_bw.write(event_id+'FMT/waveforms/data/bw.p')
        data_sw.write(event_id+'FMT/waveforms/data/sw.p')

        synthetics_bw.write(event_id+'FMT/waveforms/synthetics/bw.p')
        synthetics_sw.write(event_id+'FMT/waveforms/synthetics/sw.p')

        results_bw.save(event_id+'FMT/misfit/bw.nc')
        results_sw.save(event_id+'FMT/misfit/sw.nc')

        for _i, station in enumerate(stations):
            for key in attrs_bw[_i]:
                filename = event_id+'FMT/misfit/bw/'+station.id+key
                save_json(filename, attrs_bw[_i][key])

            for key in attrs_sw[_i]:
                filename = event_id+'FMT/misfit/sw/'+station.id+key
                save_json(filename, attrs_sw[_i][key])

        print('\nFinished\n')
