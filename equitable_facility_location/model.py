# equitable facility location model 

import pyomo.environ as pyo
import pandas as pd

def minimize_kpede_model(orig_df, dest_df, dist_df, num_locations, aversion=-1, min_percent=0, radius=-99, scaling_factor=-99, capacity=-99):
    """Build pyomo facility location model that minimizes the Kolm-Pollak EDE

    Keyword arguments:
    orig_df -- dataframe (id, population)
    dest_df -- dataframe (id, [open], [preference], [capacity])
    dist_df -- dataframe (origin, destination, distance)
    num_locations -- number of locations to open
    aversion -- aversion to inequality (default: -1)
    min_percent -- decimal percent of "percent" destinations that must open (default: 0)
    radius -- remove distances exceeding radius (default: include all distances)
    scaling_factor -- set your own value for alpha 
    (default: use "force" OR "percent" OR "all" destinations in that order)
    capacity -- used for destinations with no capacities in dest_df (default: no capacity)
    """
    errors = []

    dist_df = apply_radius(dist_df, radius=-99)
    dest_df = dest_df.query(f'id in {set(dist_df['destinations'])}')
    destinations = list(dest_df['id'])
    # stop if there aren't enough destinations
    if len(destinations)<num_locations:
        errors.append(f'infeasible: fewer than num_locations={num_locations} destinations supplied')
        return errors
    
    open_destinations = get_open(dest_df)
    percent_destinations = get_percent_open(dest_df)
    min_percent_open = math.floor(len(percent_destinations)*min_percent)
    # stop if more destinations MUST be opened than num_locations
    min_to_open = len(open_destinations) + min_percent_open
    if min_to_open > num_locations:
        errors.append('infeasible: {min_to_open} (> num_locations={num_locations}) destinations must open')
    
    origins = list(orig_df['id'])
    orig_dest_pairs = list(zip(dist_df['origin'], dist_df['destination']))

    # Dan: where should I put these methods?
    def apply_radius(dist_df, radius):
        # apply the radius to the distance file
        errors=[]
        warnings=[]

        if radius == -99:
            return dist_df
        dist_df = dist_df.query(f'distance <= {radius}')
        omitted_destinations = set(dest_df['id']) - set(dist_df['destination'])
        omitted_origins = set(orig_df['id']) - set(dist_df['origin'])
        if len(omitted_destinations) > 0:
            warnings.append(f'radius={radius} excludes {len(omitted_destinations)} destinations')
        if len(omitted_origins) > 0:
            errors.append(f'infeasible: radius={radius} excludes {len(omitted_origins)} origins')
            return errors
        
        return dist_df
    def get_open(dest_df):
        open_destinations = []
        if open in set(dest_df.columns.values):
            open_destinations = list(dest_df.query('force')['id'])
        return open_destinations
    def get_percent_open(dest_df):
        percent_destinations = []
        if open in set(dest_df.columns.values):
            percent_destinations = list(dest_df.query('percent')['id'])
        return percent_destinations
    

    model = pyo.ConcreteModel()



    model.x = pyo.Var(destinations, domain=pyo.Binary)
    model.y = pyo.Var()

    return model


# minimize_locations_model(orig_df, dest_df, dist_df, model_params):

