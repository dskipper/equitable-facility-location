# test_datalib.py

import sys
import os
import pytest
import datalib

# Fixture to create instance of origin FileInfo
@pytest.fixture
def origin_file_info():
    file_info = datalib.FileInfo(
        'origin file',
        required_cols=[
            datalib.Column('id', is_unique=True, nullable=False),
            datalib.Column('population', is_numeric=True, nullable=False)
        ]
    )
    return file_info

@pytest.fixture
def dest_file_info(): 
    file_info = datalib.FileInfo(
        'destination file',
        required_cols=[
            datalib.Column('id', is_unique=True, nullable=False)
        ],
        optional_cols=[
            datalib.Column('open', valid_values=['force','percent']),
            datalib.Column('preference', valid_values=[-3,-2,-1,0,1,2,3]),
            datalib.Column('capacity', is_numeric=True)
        ]
    )
    return file_info

@pytest.fixture
def dist_file_info():
    file_info = datalib.FileInfo(
        'distances file',
        required_cols=[
            datalib.Column('origin', is_unique=True, nullable=False),
            datalib.Column('destination', is_unique=True, nullable=False), 
            datalib.Column('distance', is_numeric=True, nullable=False)
        ]
    )
    return file_info

test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../test_data/'

# verify that the basic correct files don't generate errors
def test_check_data_origins(origin_file_info):
    csv_path = test_data_path+'origins_basic.csv'
    assert datalib.check_data(csv_path, origin_file_info) == []

def test_check_data_dests(dest_file_info):
    csv_path = test_data_path+'destinations_basic.csv'
    assert datalib.check_data(csv_path, dest_file_info) == []

def test_check_data_dist_int(dist_file_info):
    csv_path = test_data_path+'distances_taxi.csv'
    assert datalib.check_data(csv_path, dist_file_info) == []

# test for a misnamed column
def test_check_data_misnamed_col(origin_file_info):
    csv_path = test_data_path+'edge_cases/origins_columns.csv'
    assert (datalib.check_data(csv_path, origin_file_info) 
            == ["Missing required columns: {'population'}"])

# test for unrecognized column
def test_check_data_extra_col(dest_file_info):
    csv_path = test_data_path+'edge_cases/destinations_columns.csv'
    assert (datalib.check_data(csv_path, dest_file_info)
            == ["Unrecognized columns: {'population'}"])