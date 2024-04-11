import pandas as pd
import numpy as np

def get_alpha(assignment_df):
    """calculate alpha = sum pop*dist / sum pop*dist^2

    arguments:
    assignment_df -- columns: origin, destination, population, distance
    (one row per origin)
    """
    df = assignment_df.assign(
            z = lambda x: x['distance']*x['population'],
            zsquared = lambda x: x['z']**2
        )

    alpha = df['z'].sum()/df['zsquared'].sum()
    return alpha

def get_kp(assignment_df, epsilon):
    """calculate the Kolm-Pollak score

    Arguments:
    assignment_df -- columns: origin, destination, population, distance (one row per origin)
    epsilon -- aversion to inequality parameter
    """
    if epsilon==0:
        return get_mean_distance(assignment_df)
    
    alpha = float(get_alpha(assignment_df))
    kappa = alpha * epsilon
    df = (
        assignment_df
        .assign( 
            coef = lambda x: x['population']*np.exp(-kappa*x['distance'])
        )
    )
    total_pop = df['population'].sum()

    kp = -1/kappa * np.log(1/total_pop * df['coef'].sum())

    return kp

def get_mean_distance(assignment_df):
    """calculate the average distance
    
    Argument:
    assignment_df -- columns: origin, destination, population, distance (one row per origin)
    """
    df = (
        assignment_df
        .assign(
            weighted_dist = lambda x: x['population']*x['distance']
        )
    )
    total_pop = df['population'].sum()

    avg_dist = df['weighted_dist'].sum()/total_pop

    return avg_dist

