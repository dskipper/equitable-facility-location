import sys
import os
sys.path.append(os.path.dirname(__file__))
import datalib
import model
import pandas as pd

# define three file types used for model data input
orig_file_info = datalib.FileInfo(
    'origin file',
    required_cols=[
        datalib.Column('id', unique=True, nullable=False),
        datalib.Column('population', numeric=True, nullable=False)
    ]
)
dest_file_info = datalib.FileInfo(
    'destination file',
    required_cols=[
        datalib.Column('id', unique=True, nullable=False)
    ],
    optional_cols=[
        datalib.Column('open', valid_values=['yes','percent']),
        datalib.Column('preference', valid_values=[-3,-2,-1,0,1,2,3]),
        datalib.Column('capacity', numeric=True)
    ]
)
dist_file_info = datalib.FileInfo(
    'distances file',
    required_cols=[
        datalib.Column('origin', nullable=False),
        datalib.Column('destination', nullable=False), 
        datalib.Column('distance', numeric=True, nullable=False)
    ]
)

test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../data/test_data/'
orig_file_path = test_data_path+'origins_basic.csv'
dest_file_path = test_data_path+'destinations_basic.csv'
dist_lookup_path = test_data_path+'distances_cartesian.csv'

# check if all the data looks ok; exit if not
# should these functions take paths and return dataframes if everything is fine? (how?)
errors = []
errors.append(datalib.check_data(orig_file_path, orig_file_info))
errors.append(datalib.check_data(dest_file_path, dest_file_info))
errors.append(datalib.check_data(dist_lookup_path, dist_file_info))
if len(errors):
    print(errors)  # this shouldn't print anything if there aren't any errors
    # how do I make it exit if there are data errors?

# generate dataframes for model
orig_df = datalib.clean_origins(pd.read_csv(orig_file_path))
dest_df = pd.read_csv(dest_file_path)
dist_lookup_df = pd.read_csv(dist_lookup_path)
dist_df = datalib.build_dist_df(orig_df, dest_df, dist_lookup_df)

efl_model = model.minimize_kpede_model(orig_df, dest_df, dist_df, 5)


# data handling tests below
# need to: 
# figure out how to handle errors gracefully
# move these tests into the test module
test_data_path = os.path.dirname(os.path.abspath(__file__))+'/../data/test_data/'
edge_case_path = test_data_path+'edge_cases/'

# test check of correct origin file
csv_path = test_data_path+'origins_basic.csv'
print(datalib.check_data(csv_path, orig_file_info)==[])

# test cleaning of origin file
csv_path = test_data_path+'origins_basic.csv'
orig_df = datalib.clean_origins(pd.read_csv(csv_path))
print(orig_df.shape[0]==30)
# Dan: what do I do with the errors I'm returning? 
# Can I return a df OR an error?

# test check of correct destination file
csv_path = test_data_path+'destinations_basic.csv'
print(datalib.check_data(csv_path, dest_file_info)==[])
dest_df = pd.read_csv(csv_path)

# test check of correct floating point distance lookup file
csv_path = test_data_path+'distances_cartesian.csv'
print(datalib.check_data(csv_path, dist_file_info)==[])
# generate distance lookup df using cartesian distances
dist_lookup = pd.read_csv(csv_path)

# test check of correct integer distance lookup file
csv_path = test_data_path+'distances_taxi.csv'
print(datalib.check_data(csv_path, dist_file_info)==[])

# test creation of distance file with good files
dist_df = datalib.build_dist_df(orig_df, dest_df, dist_lookup)
print(dist_df.shape[0]==300)

# test missing column
csv_path = edge_case_path+'origins_missing_required_column.csv'
print(datalib.check_data(csv_path, orig_file_info)==
      ["Missing required columns: {'population'}"])

# test unrecognized column
csv_path = edge_case_path+'destinations_unrecognized_column.csv'
print(datalib.check_data(csv_path, dest_file_info)==
      ["Unrecognized columns: {'opencode'}"])

# test missing values
csv_path = edge_case_path+'origins_nan_populations.csv'
print(datalib.check_data(csv_path, orig_file_info)==
      ["Columns with missing data: ['population']"])

# test duplicate values
csv_path = edge_case_path+'origins_id_not_unique.csv'
print(datalib.check_data(csv_path, orig_file_info)==
      ["Columns with duplicate entries: ['id']"])

# test for non-numeric values
csv_path = edge_case_path+'distances_not_numeric.csv'
print(datalib.check_data(csv_path, dist_file_info)==
      ["Columns with non-numeric data: ['distance']"])

# test for invalid values
csv_path = edge_case_path+'destinations_invalid_values.csv'
print(datalib.check_data(csv_path, dest_file_info)==
      ["Invalid values in column 'open': ['closed', 'open'] not among ['yes', 'percent']", 
       "Invalid values in column 'preference': [5, 'open'] not among [-3, -2, -1, 0, 1, 2, 3]"])

# test compiling origin file with nonpositive populations
csv_path = edge_case_path+'origins_nonpos_populations.csv'
df = pd.read_csv(csv_path)
origin_df = datalib.clean_origins(df)
print(origin_df.shape[0]==25)