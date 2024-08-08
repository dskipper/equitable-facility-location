# equitable facility location model 

import pyomo.environ as pyo
import pandas as pd
import logging
import math
import numpy as np
import efl.utils as utils
import time
from collections import defaultdict

class Results:
    def __init__(self, assignment_df, parameters_dict, solver_mip_gap, solver_wall_time):
        self.assignment_df = assignment_df # origin, destination, population, distance
        self.parameters_dict = parameters_dict # input parameters
        self.solver_mip_gap = solver_mip_gap
        self.solver_wall_time = solver_wall_time

    def ede_out(self, aversion=None):
        if not aversion:
            try:
                aversion = self.parameters_dict['aversion']
            except:
                print('No aversion parameter value supplied')
        return utils.get_kp(self.assignment_df, aversion)
    
    def mean_distance_out(self):
        return utils.get_mean_distance(self.assignment_df)
    
    def scaling_factor_out(self):
        return utils.get_alpha(self.assignment_df)
    
    def num_locations_out(self):
        return self.assignment_df['destination'].nunique()
    
    def percent_covered_out(self, iso_radius):
        return utils.get_percent_covered(self.assignment_df, iso_radius)
    
    # actual aversion
    def aversion_out(self):
        kappa_in = self.parameters_dict['aversion'] * self.parameters_dict['scaling_factor']
        return kappa_in / self.scaling_factor_out()
    

def _apply_radius(orig_df, dest_df, dist_df, radius):
    # apply the radius to the distance file

    if radius == None:
        return dist_df
    dist_df = dist_df.query(f'distance <= {radius}')
    omitted_destinations = set(dest_df['id']) - set(dist_df['destination'])
    omitted_origins = set(orig_df['id']) - set(dist_df['origin'])
    if len(omitted_destinations) > 0:
        logging.warning(f'radius={radius} excludes {len(omitted_destinations)} destinations')
    if len(omitted_origins) > 0:
        raise ValueError(f'infeasible: radius={radius} excludes {len(omitted_origins)} origins')  # Dan: should this be a Value error?
    
    return dist_df

def _get_open(dest_df):
    open_destinations = []
    if 'open' in set(dest_df.columns.values):
        open_destinations = list(dest_df.query('open=="yes"')['id'])
    return open_destinations

def _get_percent_open(dest_df):
    percent_destinations = []
    if 'open' in set(dest_df.columns.values):
        percent_destinations = list(dest_df.query('open=="percent"')['id'])
    return percent_destinations

def _get_alpha_approximation(dist_df, *, open_destinations=[], percent_destinations=[], alpha=None):
    """Return or calculate alpha. 
    Use the minimum distance of each origin to 
    open destinations, percent destinations, or 
    all destinations (in that order)"""
    if alpha != None:
        return alpha
    if len(open_destinations)>0:
        alpha_dist_df = dist_df[dist_df.destination.isin(set(open_destinations))]
    elif len(percent_destinations)>0:
        alpha_dist_df = dist_df[dist_df.destination.isin(set(percent_destinations))]
    else:
        alpha_dist_df = dist_df
      
    alpa_assignment_df = (
        alpha_dist_df
        .groupby(['origin','population'])
        .agg( distance = ('distance', 'min'))
        .reset_index()
    )

    alpha = utils.get_alpha(alpa_assignment_df)

    return alpha

def _get_kp_coefficients(dist_df, kappa):
    '''return dictionary: ((orig, dest): coeff)
    '''
    df = dist_df
    if kappa==0: # coefficients are weighted distances
        df['coef'] = df['population']*df['distance']
        # df = (
        #     dist_df
        #     .assign( 
        #         coef = lambda x: x['population']*x['distance']
        #     )
        # )     
    else: # coefficients linear kolm-pollak coefficients 
        df['coef'] = df['population']*np.exp(-kappa*df['distance'])
        # df = (
        #     dist_df
        #     .assign( 
        #         coef = lambda x: x['population']*np.exp(-kappa*x['distance'])
        #     )
        # )

    triple = list(zip(df['origin'], df['destination'], df['coef']))
    coef_dict = {(x, y):z for x, y, z in triple}

    return coef_dict

    
def optimize(orig_df, dest_df, dist_df, 
                minimize, num_locations, target_ede, *, 
                aversion=-1, scaling_factor=None, 
                min_percent=0, radius=None,
                solver='scip', time_limit=3600, mip_gap=None, 
                tee=None):
    """Build pyomo facility location model that minimizes the Kolm-Pollak EDE

    Keyword arguments:
    orig_df -- dataframe (id, population)
    dest_df -- dataframe (id, [open], [preference], [capacity])
    dist_df -- dataframe (origin, destination, population, distance)
    minimize -- 'ede' or 'locations'
    num_locations -- number of locations to open (if minimize='ede')
    target_ede -- in units of distance (if minimize='locations')
    aversion -- aversion to inequality (default: -1)
    min_percent -- decimal percent of "percent" destinations that must open (default: 0)
    radius -- remove distances exceeding radius (default: include all distances)
    scaling_factor -- set your own value for alpha 
    (default: use "force" OR "percent" OR "all" destinations in that order)
    solver -- 'scip' ('gurobi' to be added later)
    time_limit -- solver times out and returns best solution so far (seconds) (default: 3600)
    mip_gap -- solver stops when within this percent of optimal (default: 0)
    tee -- print solver output to screen (default: False)
    """

    dist_df = _apply_radius(orig_df, dest_df, dist_df, radius)
    dest_df = dest_df[dest_df.id.isin(set(dist_df['destination']))]

    # collect model sets
    origins = list(orig_df['id'])
    destinations = list(dest_df['id'])
    if minimize=='ede':
        if len(destinations)<num_locations:
            raise ValueError(f'infeasible: fewer than num_locations={num_locations} destinations supplied')
    orig_dest_pairs = list(zip(dist_df['origin'], dist_df['destination']))
    temp_dict = (
        dist_df
        .groupby('origin')
        .agg(dests = ('destination',list))
        .to_dict()
    )
    orig_to_dests = temp_dict['dests']
      
    # collect model parameters
    open_destinations = _get_open(dest_df)
    percent_destinations = _get_percent_open(dest_df)
    min_percent_open = math.ceil(len(percent_destinations)*min_percent)
    min_to_open = len(open_destinations) + min_percent_open
    if minimize=='ede':
        if min_to_open > num_locations:
            raise ValueError(f'infeasible: {min_to_open} (> num_locations={num_locations}) destinations must open')

    alpha = _get_alpha_approximation(dist_df, open_destinations=open_destinations, 
                       percent_destinations=percent_destinations, alpha=scaling_factor)
    kappa = aversion*alpha
    pair_to_kpcoef = _get_kp_coefficients(dist_df, kappa)

    # build model
    model = pyo.ConcreteModel()
    logging.info('adding variables')
    model.x = pyo.Var(destinations, domain=pyo.Binary)
    model.y = pyo.Var(orig_dest_pairs, domain=pyo.Binary)

    if minimize=='ede':
        # minimize the Kolm-Pollak EDE
        logging.info('adding objective')
        def obj_rule(model):
            return sum(model.y[orig,dest]*pair_to_kpcoef[orig,dest] for orig,dest in orig_dest_pairs)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # set the number of locations to open
        logging.info('adding num locations constraint')
        def num_locations_rule(model):
            return sum(model.x[dest] for dest in destinations)==num_locations
        model.num_locations = pyo.Constraint(rule=num_locations_rule)
    
    else: # minimize=='locations'
        # minimize the number of locations to open
        logging.info('building objective')
        def obj_rule(model):
            return sum(model.x[dest] for dest in destinations)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # meet target level of access
        logging.info('adding target access constraint')
        total_pop = orig_df['population'].sum()
        target_ede_base = target_ede
        if kappa<0: # adjust for kp score
            target_ede_base = np.exp(-kappa*target_ede)
        adjusted_target_ede = total_pop*target_ede_base # adjust for total pop
        def target_access_rule(model):
            return sum(model.y[orig,dest]*pair_to_kpcoef[orig,dest] 
                       for orig,dest in orig_dest_pairs) <= adjusted_target_ede
        model.target_access = pyo.Constraint(rule=target_access_rule)

    # add constraints common to both models
    _assign_to_open_constraint(model, orig_dest_pairs)
    _must_assign_constraint(model, origins, orig_to_dests)
    _set_open_constraint(model, open_destinations)
    _min_percent_open_constraint(model, percent_destinations, min_percent_open)
    _capacity_constraint(model, orig_df, dest_df, dist_df)
    logging.info('model complete')
    # model.target_access.pprint()

    # solve
    option_names = {}
    option_names['scip'] = {'time_option': 'limits/time', 'mip_gap_option':'limits/gap'}
    option_names['gurobi'] = {'time_option': 'TimeLimit', 'mip_gap_option':'MIPGap'}

    solver_name = solver
    solver = pyo.SolverFactory(solver_name)       
    if time_limit is not None:
        solver.options[option_names[solver_name]['time_option']] = time_limit
    if mip_gap is not None:
        solver.options[option_names[solver_name]['mip_gap_option']] = mip_gap
    logging.info('starting solver')
    start_time = time.time()
    solver_result = solver.solve(model, tee=tee)
    end_time = time.time()
    if not solver_result.solver.termination_condition==pyo.TerminationCondition.optimal:
        raise ValueError(f'Solver terminated with no solution: {solver_result.solver.termination_condition}')

    # pull together results
    if solver_name=='scip':
        upper = solver_result['Solver'][0]['Primal bound']
        lower = solver_result['Solver'][0]['Dual bound']
    elif solver_name=='gurobi':
        lower = float(solver_result['Problem'][0]['Lower bound'])
        upper = float(solver_result['Problem'][0]['Upper bound'])    
    mip_gap_actual = abs(lower-upper)/abs(upper)
    wall_time = end_time - start_time
    parameters = {'minimize':minimize, 'num_locations':num_locations, 
                  'target_ede':target_ede,'aversion':aversion,
                  'scaling_factor':alpha,'min_percent':min_percent, 
                  'radius':radius,
                  'solver':solver_name,'time_limit':time_limit, 
                  'mip_gap':mip_gap}
    assignment_df = _get_assignment_df(model, dist_df)

    result = Results(assignment_df, parameters, mip_gap_actual, wall_time)

    return result

def _assign_to_open_constraint(model, orig_dest_pairs):
    # don't assign an origin to a location unless it is open
    logging.info('adding assign to open constraint')
    def assign_to_open_rule(model,orig,dest):
        return model.y[orig,dest] <= model.x[dest]
    model.assign_to_open = pyo.Constraint(orig_dest_pairs, rule=assign_to_open_rule)

def _must_assign_constraint(model, origins, orig_to_dests):
    # must assign each origin to a destination
    logging.info('adding must assign constraint')
    def must_assign_rule(model,orig):
        return sum(model.y[orig,dest] for dest in orig_to_dests[orig])==1
    model.must_assign = pyo.Constraint(origins, rule=must_assign_rule)

def _set_open_constraint(model, open_destinations):
    # set open destinations to open
    if len(open_destinations)==0:
        return
    logging.info('adding set open constraint')
    def set_open_rule(model,dest):
        return model.x[dest]==1
    model.set_open = pyo.Constraint(open_destinations, rule=set_open_rule)

def _min_percent_open_constraint(model, percent_destinations, min_open):    
    # open minimum number of percent_open destinations
    if len(percent_destinations)==0:
        return
    logging.info('adding min percent open constraint')
    def min_percent_open_rule(model):
        return sum(model.x[dest] for dest in percent_destinations)>=min_open
    model.min_percent_open = pyo.Constraint(rule=min_percent_open_rule)

def _capacity_constraint(model, orig_df, dest_df, dist_df):
    if not 'capacity' in set(dest_df.columns.values):
        return 
    cap_dest_df = dest_df.query('capacity.notna()')
    if cap_dest_df.shape[0]==0:
        return
    logging.info('adding capacity constraint')
    capped_dests = set(cap_dest_df['id'])
    temp_dict = (
        dist_df
        .query('destination in @capped_dests')
        .groupby('destination')
        .agg(origs = ('origin',list))
        .to_dict()
    )
    capped_dest_to_origs = temp_dict['origs']
    orig_to_pop = {orig:pop for orig,pop in zip(orig_df['id'],orig_df['population'])}
    dest_to_cap = {dest:cap for dest,cap in zip(cap_dest_df['id'],cap_dest_df['capacity'])}
    # restrict capacity of each destination as appropriate
    def capacity_rule(model,dest):
        return (sum(model.y[orig,dest]*orig_to_pop[orig] 
                    for orig in capped_dest_to_origs[dest])<=dest_to_cap[dest])
    model.capacity = pyo.Constraint(capped_dests, rule=capacity_rule)

# mip_gap default = scip gap default = 0
def solve_model(model, *, mip_solver='scip', time_limit=3600, mip_gap=0, tee=None):
    solver = pyo.SolverFactory(mip_solver)
    solver.options ={ 'limits/time': time_limit,  'limits/gap': mip_gap }

    solver_result = solver.solve(model, tee=tee)

    if solver_result.solver.termination_condition==pyo.TerminationCondition.optimal:
        return solver_result
    else:
        raise ValueError(f'Solver terminated with no solution: {solver_result.solver.termination_condition}')


def _get_assignment_df(model, dist_df):
    assignments = [(orig,dest,dist,pop) for orig,dest,dist,pop
                   in zip(dist_df['origin'],dist_df['destination'],dist_df['distance'],dist_df['population']) 
                   if model.y[orig,dest].value>0.9] # this handles floating point errors (sometimes 1 is not exactly 1)
    assignment_df = (
        pd.DataFrame(assignments, columns=['origin','destination','distance','population'])
    )

    return assignment_df



###### ISOCHRONE ######################################################
# Minimize the number of residents OUTSIDE x radius of k open locations
# or 
# Minimize the number of locations so that every resident is within x 
# radius of an open location
######################################################################
def optimize_isochrone(orig_df, dest_df, dist_df, iso_radius, 
                       minimize, num_locations, *, 
                       percent_coverage=1, 
                       min_percent=0, radius=None,
                       solver='scip', time_limit=3600, mip_gap=None, 
                       tee=None):
    """Build pyomo facility location model that minimizes either
    (1) number of people uncovered* by k optimally located sites
    (2) number of locations to cover* % of population
    *coverage = within iso_radius of open site
    **(Facility capacities is NOT implemented)**

    Keyword arguments:
    orig_df -- dataframe (id, population)
    dest_df -- dataframe (id, [open], [preference], [capacity])
    dist_df -- dataframe (origin, destination, population, distance)
    iso_radius -- in distance units
    minimize -- 'uncovered' or 'locations'
    num_locations -- number of locations to open (req if minimize='uncovered')

    Optional:
    percent_coverage -- % of pop that must be covered (used if minimize='locations'; default=1)
    min_percent -- decimal percent of "percent" destinations that must open (default: 0)
    radius -- remove distances exceeding radius (default: include all distances)
    solver -- 'scip' ('gurobi' to be added later)
    time_limit -- solver times out and returns best solution so far (seconds) (default: 3600)
    mip_gap -- solver stops when within this percent of optimal (default: 0)
    tee -- print solver output to screen (default: False)
    """

    dist_df = _apply_radius(orig_df, dest_df, dist_df, radius)
    dest_df = dest_df[dest_df.id.isin(set(dist_df['destination']))]

    # collect model sets
    origins = list(orig_df['id'])
    destinations = list(dest_df['id'])
    if minimize=='uncovered':
        if len(destinations)<num_locations:
            raise ValueError(f'infeasible: fewer than num_locations={num_locations} destinations supplied')
    orig_dest_pairs = list(zip(dist_df['origin'], dist_df['destination']))
      
    # collect model parameters
    open_destinations = _get_open(dest_df)
    orig_to_pop = {id:pop for id,pop in list(zip(orig_df['id'], orig_df['population']))}
    triple = list(zip(dist_df['origin'], dist_df['destination'], dist_df['distance']))
    pair_to_dist = {(x, y):z for x, y, z in triple}
    percent_destinations = _get_percent_open(dest_df)
    min_percent_open = math.ceil(len(percent_destinations)*min_percent)
    min_to_open = len(open_destinations) + min_percent_open
    if minimize=='uncovered':
        if min_to_open > num_locations:
            raise ValueError(f'infeasible: {min_to_open} (> num_locations={num_locations}) destinations must open')

    # build model
    model = pyo.ConcreteModel()
    logging.info('adding variables')
    model.x = pyo.Var(destinations, domain=pyo.Binary)
    model.y = pyo.Var(orig_dest_pairs, domain=pyo.Binary)
    model.z = pyo.Var(origins, domain=pyo.Binary)

    if minimize=='uncovered': 
        # maximize 'covered': the number of residents within iso_radius of open site
        logging.info('adding maximize coverage objective')
        def obj_rule(model):
            return sum(model.z[orig]*orig_to_pop[orig] for orig in origins)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.maximize)

        # set the number of locations to open
        logging.info('adding num locations constraint')
        def num_locations_rule(model):
            return sum(model.x[dest] for dest in destinations)==num_locations
        model.num_locations = pyo.Constraint(rule=num_locations_rule)
    
    else: # minimize=='locations'
        # minimize the number of locations to open
        logging.info('adding min locations objective')
        def obj_rule(model):
            return sum(model.x[dest] for dest in destinations)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # meet target level of isochrone coverage
        logging.info('adding percent coverage constraint')
        total_pop = orig_df['population'].sum()
        def target_coverage_rule(model):
            return ( 
                sum(model.z[orig]*orig_to_pop[orig] for orig in origins) 
                                                >= total_pop*percent_coverage 
            )
        model.target_coverage = pyo.Constraint(rule=target_coverage_rule)

    # determine if dest "covers" orig
    logging.info('adding dest covers orig constraint')
    def dest_covers_orig_rule(model,orig,dest):
        return pair_to_dist[orig,dest]*model.y[orig,dest] <= model.x[dest]*iso_radius
    model.dest_covers_orig = pyo.Constraint(orig_dest_pairs, rule=dest_covers_orig_rule)

    # determine if orig is covered
    logging.info('adding orig covered constraint')
    def orig_covered_rule(model,orig):
        return model.z[orig] <= sum(model.y[orig,dest] for dest in destinations)
    model.orig_covered = pyo.Constraint(origins, rule=orig_covered_rule)

    # add common constraints
    _set_open_constraint(model, open_destinations)
    _min_percent_open_constraint(model, percent_destinations, min_percent_open)
    ##### Don't need capacities -- maybe add later? #####
    # _capacity_constraint(model, orig_dest_pairs, orig_df, dest_df)
    logging.info('model complete')

    # solve
    option_names = {}
    option_names['scip'] = {'time_option': 'limits/time', 'mip_gap_option':'limits/gap'}
    option_names['gurobi'] = {'time_option': 'TimeLimit', 'mip_gap_option':'MIPGap'}

    solver_name = solver
    solver = pyo.SolverFactory(solver_name)       
    if time_limit is not None:
        solver.options[option_names[solver_name]['time_option']] = time_limit
    if mip_gap is not None:
        solver.options[option_names[solver_name]['mip_gap_option']] = mip_gap
    logging.info('starting solver') 
    start_time = time.time()
    solver_result = solver.solve(model, tee=tee)
    end_time = time.time()
    if not solver_result.solver.termination_condition==pyo.TerminationCondition.optimal:
        raise ValueError(f'Solver terminated with no solution: {solver_result.solver.termination_condition}')

    # pull together results
    if solver_name=='scip':
        upper = solver_result['Solver'][0]['Primal bound']
        lower = solver_result['Solver'][0]['Dual bound']
    elif solver_name=='gurobi':
        lower = float(solver_result['Problem'][0]['Lower bound'])
        upper = float(solver_result['Problem'][0]['Upper bound'])    
    mip_gap_actual = abs(lower-upper)/abs(upper)
    wall_time = end_time - start_time
    parameters = {'minimize':minimize, 'num_locations':num_locations, 
                  'iso_radius':iso_radius,'percent_coverage':percent_coverage,
                  'min_percent':min_percent, 
                  'radius':radius,
                  'solver':solver_name,'time_limit':time_limit, 
                  'mip_gap':mip_gap}
    assignment_df = _get_isochrone_assignment_df(model, origins, destinations, dist_df, orig_df)

    result = Results(assignment_df, parameters, mip_gap_actual, wall_time)

    return result

def _get_isochrone_assignment_df(model, origins, destinations, dist_df, orig_df):
           
    open_dests = [dest for dest in destinations if model.x[dest].value>0.9]
    open_dist_df = (
        dist_df
        .query(f'destination in {open_dests}')
        .drop(columns=['population'])
        .sort_values('distance')
        .groupby('origin')
        .first()
        .reset_index()
    )
    assignment_df = (
        orig_df[['id','population']]
        .rename(columns={'id':'origin'})
        .merge(open_dist_df.reset_index(drop=True),on='origin')
    )
    return assignment_df

