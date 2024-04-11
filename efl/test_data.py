# test_datalib.py

import sys
import os
import pytest
import efl.data as data
import pandas as pd

test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../data/test_data/'
edge_case_path = test_data_path+'edge_cases/'

# verify that the basic correct files don't generate errors
def test_validate_origin_df():
    csv_path = test_data_path+'origins_basic.csv'
    assert data.validate_origin_df(pd.read_csv(csv_path)).shape==(30, 2) 

def test_clean_origins():
    csv_path = test_data_path+'origins_basic.csv'
    orig_df = data.validate_origin_df(pd.read_csv(csv_path))
    assert orig_df.shape[0]==30

def test_validate_destination_df():
    csv_path = test_data_path+'destinations_basic.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path)).shape==(10, 2)

# test capacities on destinations
def test_validate_destination_df_constant_capacity():
    csv_path = test_data_path+'destinations_basic.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path), capacity=500)['capacity'].sum()==5000

def test_validate_destination_df_constant_capacity():
    csv_path = edge_case_path+'destinations_capacities.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path), capacity=500)['capacity'].sum()==5400

# test check of correct floating point distance lookup file
def test_validate_distance_df_floats():
    csv_path = test_data_path+'distances_cartesian.csv'
    assert data.validate_distance_df(pd.read_csv(csv_path)).shape==(300, 3)

# test check of correct integer distance lookup file
def test_validate_distance_df_integers():
    csv_path = test_data_path+'distances_taxi.csv'
    assert data.validate_distance_df(pd.read_csv(csv_path)).shape==(300,3)

# test creation of distance file with good files
def test_build_dist_df():
    orig_df = data.validate_origin_df(pd.read_csv(test_data_path+'origins_basic.csv'))
    dest_df = data.validate_destination_df(pd.read_csv(test_data_path+'destinations_basic.csv'))
    dist_lookup = data.validate_distance_df(pd.read_csv(test_data_path+'distances_cartesian.csv'))
    dist_df = data.build_dist_df(orig_df, dest_df, dist_lookup)
    assert dist_df.shape==(300, 4)

# test missing column
def test_missing_column():
    csv_path = edge_case_path+'origins_missing_required_column.csv'
    assert data.validate_origin_df(pd.read_csv(csv_path))==None

# test optional column with no data
def test_no_data():
    csv_path = edge_case_path+'destinations_no_data_in_optional_column.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path)).shape==(10,2)
    
# test unrecognized column
def test_unrecognized_column():
    csv_path = edge_case_path+'destinations_unrecognized_column.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path))==None

# test missing values
def test_missing_data():
    csv_path = edge_case_path+'origins_nan_populations.csv'
    assert data.validate_origin_df(pd.read_csv(csv_path))==None

# test duplicate values
def test_duplicate_values():
    csv_path = edge_case_path+'origins_id_not_unique.csv'
    assert data.validate_origin_df(pd.read_csv(csv_path))==None

# test for non-numeric values
def test_non_numeric():
    csv_path = edge_case_path+'distances_not_numeric.csv'
    assert data.validate_distance_df(pd.read_csv(csv_path))==None

# test for invalid values
def test_invalid_values():
    csv_path = edge_case_path+'destinations_invalid_values.csv'
    assert data.validate_destination_df(pd.read_csv(csv_path))==None

# test cleaning origin file with nonpositive populations
def test_negative_zero_populations():
    csv_path = edge_case_path+'origins_nonpos_populations.csv'
    df = data.validate_origin_df(pd.read_csv(csv_path))
    assert df.shape==(25, 2)