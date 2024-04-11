import sys
import os
import efl.optimize as optimize
import pandas as pd
import pytest

test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../data/test_data/'
edge_case_path = test_data_path+'edge_cases/'
test_df_path = test_data_path+'dataframes/'

# some basic input files to try lots of different options on
orig_df = pd.read_csv(test_df_path+'orig_df.csv')
dest_df = pd.read_csv(test_df_path+'dest_df.csv')
dist_lookup_df = pd.read_csv(test_data_path+'distances_cartesian.csv')

def test_min_ede():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6)
    assert result.ede_out()==171.4566587957021

def test_min_locations():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, minimize='locations', target_ede=190)
    assert result.num_locations_out()==6

def test_min_ede_aversion():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=-2)
    assert result.ede_out()==172.3649176581287

def test_min_ede_zero_aversion():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=0)
    assert result.ede_out()==170.55386666666666

def test_mean_distance():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=0)
    assert result.ede_out()==result.mean_distance_out()

def test_min_ede_aversion_out():    
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=-2)
    assert result.aversion_out()==-1.3371362315999302

def test_min_ede_alpha():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=-2, scaling_factor=0.0003404912083720304)
    assert result.aversion_out()==-2.0

def test2_min_ede_alpha():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, aversion=-2, scaling_factor=0.00034049120837203035)
    assert result.parameters_dict['scaling_factor']==0.00034049120837203035

def test_min_ede_minpercent():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=6, min_percent=0.5)
    percent_locations = set(dest_df.query('open=="percent"')['id'])
    optimal_locations = set(result.assignment_df['destination'])
    assert len(percent_locations)-len(percent_locations-optimal_locations)>=len(percent_locations)*0.5

def test_min_locations_radius_capacity_prep():
    dest_df = pd.read_csv(test_data_path+'destinations_no_yes_no_percent.csv')
    result = optimize.run(orig_df, dest_df, dist_lookup_df, minimize='locations', target_ede=250)
    assert result.num_locations_out()==3

def test_min_locations_radius():
    dest_df = pd.read_csv(test_data_path+'destinations_no_yes_no_percent.csv')
    result = optimize.run(orig_df, dest_df, dist_lookup_df, minimize='locations', target_ede=250, radius=370)
    assert result.num_locations_out()==4

def test_min_locations_zero_aversion():
    dest_df = pd.read_csv(test_data_path+'destinations_no_yes_no_percent.csv')
    result = optimize.run(orig_df, dest_df, dist_lookup_df, minimize='locations', aversion=0, target_ede=250)
    assert result.num_locations_out()==3

def test_min_ede_capacity():
    dest_df = pd.read_csv(test_data_path+'destinations_no_yes_no_percent.csv')
    result = optimize.run(orig_df, dest_df, dist_lookup_df, minimize='locations', target_ede=250, capacity=90)
    assert result.num_locations_out()==5

# Need a bigger test problem to test solver parameters
# def test_mip_gap():
#     # mip_gap is a percent listed as a decimal
#     dest_df = pd.read_csv(test_data_path+'destinations_basic.csv')
#     result = efl.run(orig_df, dest_df, dist_lookup_df, minimize='ede', num_locations=7, capacity=60, mip_gap=0.0062) # = 0.63 %
#     assert result.parameters_dict['mip_gap_actual'] >= 0.0062

@pytest.mark.skip(reason="requires gurobi executable and license")
def test_mip_gap():
    result = optimize.run(orig_df, dest_df, dist_lookup_df, num_locations=8, capacity=60, mip_gap=0.0063, solver='gurobi')
    assert round(result.solver_mip_gap,4)==0.0026

def test_out_file():
    dest_df = pd.read_csv(test_data_path+'destinations_no_yes_no_percent.csv')
    out_path = test_data_path+'results/out_from_run.csv'
    result = optimize.run(orig_df, dest_df, dist_lookup_df, out_file=out_path, minimize='locations', target_ede=250, capacity=90)
    assert result.num_locations_out()==5

