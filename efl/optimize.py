import sys
import os
#sys.path.append(os.path.dirname(__file__))
import efl.data as data
import efl.model as model
import pandas as pd
import click

@click.command()
@click.argument('origin_file', type=click.File('r'))
@click.argument('destination_file', type=click.File('r'))
@click.argument('distance_file', type=click.File('r'))
@click.argument('out_file', type=click.File('w'))
@click.option('--minimize', default='ede', type=click.Choice(['ede', 'locations'], case_sensitive=False),
              help='value to minimize (default: ede)')
@click.option('--num_locations', type=click.IntRange(1,), 
              help='number of locations to open (required if minimize=ede)')
@click.option('--target_ede', type=click.FloatRange(0,max=None,min_open=True), 
              help='lower bound on ede (required if minimize=locations)')
@click.option('--aversion', default=-1, type=click.FloatRange(min=None,max=0), 
              help='aversion to inequality parameter (default: -1)')
@click.option('--scaling_factor', type=click.FloatRange(0,max=None,min_open=True),
              help='("alpha") default: estimate based on data')
@click.option('--min_percent', default=0, type=click.FloatRange(0,1),
              help='minimum percentage of "percent" destinations to open (default: 0)')
@click.option('--radius', type=click.FloatRange(0,max=None,min_open=True), 
              help='maximum distance that can be assigned (default: none)')
@click.option('--capacity', default=None, type=click.FloatRange(0,max=None,min_open=True), 
              help='capacity on all destinations not capacitated in destinations file (default: none)')
@click.option('--solver', default='scip', type=click.Choice(['scip', 'gurobi'], case_sensitive=False),
              help='(default: scip)')
@click.option('--time_limit', default=None, type=click.FloatRange(0,max=None,min_open=True), 
              help='solver: time limit in seconds (returns best solutions so far)')
@click.option('--mip_gap', default=None, type=click.FloatRange(0,1,min_open=True,max_open=True), 
              help='solver: MIP optimality gap')

def cli(origin_file, destination_file, distance_file, out_file, *,
        minimize, num_locations, target_ede,
        aversion, scaling_factor,
        min_percent, radius, capacity,
        solver, time_limit, mip_gap):
    """Command line interface to run equitable facility location
    model and send output to two csv files:
    out_file -- origin, destination, distance, population
    out_file_params -- parameters and results summary

    Required arguments:
    origin_file -- path to origin data (csv)
    destination_file -- path to destination data (csv)
    distance_file -- path to lookup table for statistics (csv)
    out_file -- path to out file (csv)

    Keyword arguments (model):
    minimize -- 'ede' or 'locations' (default: 'ede')
    num_locations -- (required if minimize = 'ede')
    target_ede -- (required if minimize = 'locations')
    aversion -- (<0) aversion to inequality (default: -1)
    scaling_factor -- computed using data by default
    min_percent -- min % of open='percent' destinations to select (default: 0)
    radius -- max distance to include in optimization
    capacity -- assigned to destinations with no individual capacity

    Keyword arguments (solver):
    solver -- 'scip' or 'gurobi' (default: 'scip')
    time_limit -- max solver time (seconds)
    mip_gap -- min optimality gap
    """

    # check if all the data looks ok; exit if not
    print(f'cli {mip_gap =}')
    orig_df = data.validate_origin_df(pd.read_csv(origin_file))
    dest_df = data.validate_destination_df(pd.read_csv(destination_file), capacity)
    dist_lookup_df = data.validate_distance_df(pd.read_csv(distance_file))
    if any(df is None for df in [orig_df, dest_df, dist_lookup_df]):
        print('Data has errors. See logs.')
        return 1 # 1 means data error (0 means success)
    
    try:
        results = _run_optimization(orig_df, dest_df, dist_lookup_df, 
                        minimize=minimize, num_locations=num_locations, target_ede=target_ede,
                        aversion=aversion, scaling_factor=scaling_factor,
                        min_percent=min_percent, radius=radius,
                        solver=solver, time_limit=time_limit, mip_gap=mip_gap)   
    except ValueError as e:
        print(f'Error: {e}')
        return 1
    
    # add parameters that don't get passed to the model module
    results.parameters_dict['capacity'] = capacity
    results.parameters_dict['origin_file'] = origin_file.name
    results.parameters_dict['destination_file'] = destination_file.name
    results.parameters_dict['distance_file'] = distance_file.name
    results.parameters_dict['out_file'] = out_file.name

    _print_to_files(results, out_file.name)

    return 0

def run(origin_df, destination_df, distance_lookup_df, *, 
        out_file=None, minimize='ede', num_locations=None, target_ede=None,
        aversion=-1, scaling_factor=None,
        min_percent=0, radius=None, capacity=None,
        solver='scip', time_limit=None, mip_gap=None):
    """Run equitable facility location model and return
    equitable_facility_location.model.Results object

    Required arguments:
    origin_df -- origin data (pandas DataFrame)
    destination_df -- destination data (pandas DataFrame)
    distance_lookup_df -- distance lookup table (pandas DataFrame)

    Keyword arguments (model):
    out_file -- path to csv for results (default: None)
    minimize -- 'ede' or 'locations' (default: 'ede')
    num_locations -- (required if minimize = 'ede')
    target_ede -- (required if minimize = 'locations')
    aversion -- (<0) aversion to inequality (default: -1)
    scaling_factor -- computed using data by default
    min_percent -- min % of open='percent' dests to select (default: 0)
    radius -- max distance to include in optimization
    capacity -- assigned to dests with no individual capacity

    Keyword arguments (solver):
    solver -- 'scip' or 'gurobi' (default: 'scip')
    time_limit -- max solver time (seconds)
    mip_gap -- min optimality gap
    """
    
    orig_df = data.validate_origin_df(origin_df)
    dest_df = data.validate_destination_df(destination_df, capacity)
    dist_lookup_df = data.validate_distance_df(distance_lookup_df)
    if any(df is None for df in [orig_df, dest_df, dist_lookup_df]):
        print('Data has errors. See logs.')
        return 1 # 1 means data error (0 means success)
    
    try:
        results = _run_optimization(orig_df, dest_df, dist_lookup_df, 
                            minimize=minimize, num_locations=num_locations, target_ede=target_ede,
                            aversion=aversion, scaling_factor=scaling_factor,
                            min_percent=min_percent, radius=radius,
                            solver=solver, time_limit=time_limit, mip_gap=mip_gap)
    except ValueError as e:
        print(f'Error: {e}')
        return 1

    # add parameters that don't get passed to the model module
    results.parameters_dict['capacity'] = capacity
    results.parameters_dict['out_file'] = out_file
    if out_file is not None:
        _print_to_files(results, out_file)

    return results

def _run_optimization(orig_df, dest_df, dist_lookup_df, *, 
            minimize='ede', num_locations=None, target_ede=None,
            aversion=-1, scaling_factor=None,
            min_percent=0, radius=None,
            solver='scip', time_limit=None, mip_gap=None):
    
    if minimize=='ede' and num_locations is None:
        raise ValueError(f'if minimize=ede then num_locations must be set')
    if minimize=='locations' and target_ede is None:
        raise ValueError(f'if minimize=locations then target_ede must be set')
    
    dist_df = data.build_dist_df(orig_df, dest_df, dist_lookup_df)
    if dist_df is None:
        print('Data has errors. See logs.')
        return 1
    
    print(f'minimizing {minimize}')
    results = model.optimize(
                        orig_df, dest_df, dist_df, minimize,
                        num_locations, target_ede,
                        aversion=aversion, scaling_factor=scaling_factor,
                        min_percent=min_percent, radius=radius,
                        solver=solver, time_limit=time_limit, mip_gap=mip_gap
                        )

    return results

def _print_to_files(results, out_file):
    out_file_stripped = _remove_csv(out_file)
    summary_dict = results.parameters_dict.copy()
    summary_dict['solver_wall_time'] = results.solver_wall_time
    summary_dict['solver_mip_gap'] = results.solver_mip_gap
    summary_dict['aversion_out'] = results.aversion_out()
    summary_dict['scaling_factor_out'] = results.scaling_factor_out()
    summary_dict['num_locations_out'] = results.num_locations_out()
    summary_dict['mean_distance_out'] = results.mean_distance_out()
    summary_dict['ede_out'] = results.ede_out()
    summary_df = pd.DataFrame(summary_dict.items(), columns=['parameter','value'])

    results.assignment_df.to_csv(out_file_stripped+'.csv', index=False)
    summary_df.to_csv(out_file_stripped+'_summary.csv', index=False)

    return 0

def _remove_csv(out_file):
    # remove '.csv' at end of out_file path
    s = '.'
    x = out_file.split(s)
    if x[len(x)-1]=='csv':
        x_trimmed = x[0:len(x)-1]
        out_file_trimmed = s.join(x_trimmed)
    else:
        out_file_trimmed = out_file
    return out_file_trimmed

if __name__=='__main__':
   cli()
