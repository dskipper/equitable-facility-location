# equitable facility location model 

import pyomo.environ as pyo
import pandas as pd
import logging
import math
import numpy as np
import efl.utils as utils
import time

class Results:
    def __init__(self, assignment_df, parameters_dict, solver_mip_gap, solver_wall_time):
        self.assignment_df = assignment_df # origin, destination, population, distance
        self.parameters_dict = parameters_dict # input parameters
        self.solver_mip_gap = solver_mip_gap
        self.solver_wall_time = solver_wall_time

    def ede_out(self):
        return utils.get_kp(self.assignment_df, self.parameters_dict['aversion'])
    
    def mean_distance_out(self):
        return utils.get_mean_distance(self.assignment_df)
    
    def scaling_factor_out(self):
        return utils.get_alpha(self.assignment_df)
    
    def num_locations_out(self):
        return self.assignment_df['destination'].nunique()
    
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
                solver='scip', time_limit=3600, mip_gap=None):
    """Build pyomo facility location model that minimizes the Kolm-Pollak EDE

    Keyword arguments:
    orig_df -- dataframe (id, population)
    dest_df -- dataframe (id, [open], [preference], [capacity])
    dist_df -- dataframe (origin, destination, population, distance)
    num_locations -- number of locations to open
    aversion -- aversion to inequality (default: -1)
    min_percent -- decimal percent of "percent" destinations that must open (default: 0)
    radius -- remove distances exceeding radius (default: include all distances)
    scaling_factor -- set your own value for alpha 
    (default: use "force" OR "percent" OR "all" destinations in that order)
    solver -- 'scip' ('gurobi' to be added later)
    time_limit -- solver times out and returns best solution so far (seconds) (default: 3600)
    mip_gap -- solver stops when within this percent of optimal (default: 0)
    """

    dist_df = _apply_radius(orig_df, dest_df, dist_df, radius)
    dest_df = dest_df[dest_df.id.isin(set(dist_df['destination']))]

    # collect model sets
    destinations = list(dest_df['id'])
    if minimize=='ede':
        if len(destinations)<num_locations:
            raise ValueError(f'infeasible: fewer than num_locations={num_locations} destinations supplied')
    orig_dest_pairs = list(zip(dist_df['origin'], dist_df['destination']))
      
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
    model.x = pyo.Var(destinations, domain=pyo.Binary)
    model.y = pyo.Var(orig_dest_pairs, domain=pyo.Binary)

    if minimize=='ede':
        # minimize the Kolm-Pollak EDE
        def obj_rule(model):
            return sum(model.y[orig,dest]*pair_to_kpcoef[orig,dest] for orig,dest in orig_dest_pairs)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # set the number of locations to open
        def num_locations_rule(model):
            return sum(model.x[dest] for dest in destinations)==num_locations
        model.num_locations = pyo.Constraint(rule=num_locations_rule)
    
    else: # minimize=='locations'
        # minimize the number of locations to open
        def obj_rule(model):
            return sum(model.x[dest] for dest in destinations)
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # meet target level of access
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
    _must_assign_constraint(model, orig_df, orig_dest_pairs)
    _set_open_constraint(model, open_destinations)
    _min_percent_open_constraint(model, percent_destinations, min_percent_open)
    _capacity_constraint(model, orig_dest_pairs, orig_df, dest_df)
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
    start_time = time.time()
    solver_result = solver.solve(model, tee=True)
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
    def assign_to_open_rule(model,orig,dest):
        return model.y[orig,dest] <= model.x[dest]
    model.assign_to_open = pyo.Constraint(orig_dest_pairs, rule=assign_to_open_rule)

def _must_assign_constraint(model, orig_df, orig_dest_pairs):
    # must assign each origin to a destination
    origins = list(orig_df['id'])
    orig_to_destinations = {orig:[y for x,y in orig_dest_pairs if x==orig] for orig in origins}
    def must_assign_rule(model,orig):
        return sum(model.y[orig,dest] for dest in orig_to_destinations[orig])==1
    model.must_assign = pyo.Constraint(origins, rule=must_assign_rule)

def _set_open_constraint(model, open_destinations):
    # set open destinations to open
    def set_open_rule(model,dest):
        return model.x[dest]==1
    if len(open_destinations)>0:
        model.set_open = pyo.Constraint(open_destinations, rule=set_open_rule)

def _min_percent_open_constraint(model, percent_destinations, min_open):    
    # open minimum number of percent_open destinations
    def min_percent_open_rule(model):
        return sum(model.x[dest] for dest in percent_destinations)>=min_open
    if len(percent_destinations)>0:
        model.min_percent_open = pyo.Constraint(rule=min_percent_open_rule)

def _capacity_constraint(model, orig_dest_pairs, orig_df, dest_df):
    if not 'capacity' in set(dest_df.columns.values):
        return 
    cap_dest_df = dest_df.query('capacity.notna()')
    if cap_dest_df.shape[0]==0:
        return
    orig_to_pop = {orig:pop for orig,pop in zip(orig_df['id'],orig_df['population'])}
    dest_to_cap = {dest:cap for dest,cap in zip(cap_dest_df['id'],cap_dest_df['capacity'])}
    cap_destinations = list(dest_to_cap.keys())
    dest_to_origins = {dest:[x for x,y in orig_dest_pairs if y==dest] for dest in cap_destinations}
    # restrict capacity of each destination as appropriate
    def capacity_rule(model,dest):
        return sum(model.y[orig,dest]*orig_to_pop[orig] for orig in dest_to_origins[dest])<=dest_to_cap[dest]
    if dest_to_cap != None:
        model.capacity = pyo.Constraint(cap_destinations, rule=capacity_rule)


# mip_gap default = scip gap default = 0
def solve_model(model, dist_df, *, mip_solver='scip', time_limit=3600, mip_gap=0):
    solver = pyo.SolverFactory(mip_solver)
    solver.options ={ 'limits/time': time_limit,  'limits/gap': mip_gap }

    solver_result = solver.solve(model, tee=True)

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

