# test_datalib.py

import sys
import os
import pytest
import efl.data as data
import efl.model as model
import pandas as pd

test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../data/test_data/'
edge_case_path = test_data_path+'edge_cases/'
test_df_path = test_data_path+'dataframes/'

orig_df = pd.read_csv(test_df_path+'orig_df.csv')
dest_df = pd.read_csv(test_df_path+'dest_df.csv')
dist_df = pd.read_csv(test_df_path+'dist_df.csv')
open_destinations = ['dest1','dest3','dest4']
kappa = -0.00022764156562774166

# one destination is eliminated (warning)
def test_apply_radius_omit_dest():
    dest_df = data.validate_destination_df(pd.read_csv(edge_case_path+'destinations_dest_far_away.csv'))
    dist_lookup = data.validate_distance_df(pd.read_csv(edge_case_path+'distances_dest_far_away.csv'))
    dist_df = data.build_dist_df(orig_df, dest_df, dist_lookup)
    new_dist_df = model._apply_radius(orig_df, dest_df, dist_df, 1000)
    assert new_dist_df.shape==(299,4)

# one origin is eliminated (error)
def test_apply_radius_omit_orig():
    has_error = 0
    try:
        new_dist_df = model._apply_radius(orig_df, dest_df, dist_df, 300)
    except ValueError as e:
        print(e)
        has_error = 1
    assert has_error==1

def test_get_open():
    dest_df = data.validate_destination_df(pd.read_csv(edge_case_path+'destinations_2_yes_3_percent.csv'))
    open_destinations = model._get_open(dest_df)
    assert len(open_destinations)==2

def test_get_percent():
    dest_df = data.validate_destination_df(pd.read_csv(edge_case_path+'destinations_2_yes_3_percent.csv'))
    percent_destinations = model._get_percent_open(dest_df)
    assert len(percent_destinations)==3

# calculate alpha
def test_get_alpha():
    alpha = model._get_alpha_approximation(dist_df, open_destinations=open_destinations)
    assert alpha==0.00022764156562774166

# pass through alpha
def test_return_alpha():  
    scaling_factor = 0.0003
    alpha = model._get_alpha_approximation(dist_df, open_destinations=open_destinations, alpha=scaling_factor)
    assert alpha==0.0003

def test_get_kp_coefficients():
    obj_coef_df = model._get_kp_coefficients(dist_df, kappa)
    assert obj_coef_df['orig24', 'dest6']==8.359123688807468