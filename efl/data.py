import pandas as pd
from itertools import product
import numpy as np
from dataclasses import dataclass, field
import logging

@dataclass
class Column:
    name: str
    unique: bool=False
    numeric: bool=False
    nullable: bool=True
    valid_values: list[str]=field(default_factory=list) #field returns empty list

@dataclass
class FileInfo:
    name: str
    required_cols: list[Column] #required, so no default value
    optional_cols: list[Column]=field(default_factory=list)

def validate_destination_df(df, capacity=None):
    file_info = FileInfo(
        'destination file',
        required_cols=[
            Column('id', unique=True, nullable=False)
        ],
        optional_cols=[
            Column('open', valid_values=['yes','percent']),
            Column('preference', valid_values=[-3,-2,-1,0,1,2,3]),
            Column('capacity', numeric=True)
        ]
    )
    df = _validate_data(df, file_info)
    df = _include_capacity(df, capacity)

    return df

# only for destination df
def _include_capacity(df, capacity):
    df = df
    if (not df is None) and (capacity):
        if 'capacity' in set(df.columns.values):
            df = (
                df
                .assign( 
                    capacity = lambda x: x['capacity'].fillna(capacity)
                )
            )
        else:
            df['capacity'] = capacity

    return df

def validate_distance_df(df):
    file_info = FileInfo(
        'distances file',
        required_cols=[
            Column('origin', nullable=False),
            Column('destination', nullable=False), 
            Column('distance', numeric=True, nullable=False)
        ]
    )
    return _validate_data(df, file_info)

def validate_origin_df(df):
    file_info = FileInfo(
        'origin file',
        required_cols=[
            Column('id', unique=True, nullable=False),
            Column('population', numeric=True, nullable=False)
        ]
    )
    df = _validate_data(df, file_info)
    df = _clean_origins(df)
    return df

# check if data file has the correct attributes
def _validate_data(df, file_info):
    """Validates data and returns dataframe or None if data is invalid
    """
    has_error = False
    col_names = set(df.columns.values)

    # test if data has required columns
    required = {col.name for col in file_info.required_cols}
    missing_cols = required - col_names
    if len(missing_cols)>0:
        logging.error(f'Missing required columns: {missing_cols}')
        has_error = True
    
    # test if there are unrecognized columns
    optional = {col.name for col in file_info.optional_cols}
    extra_cols = col_names - (optional | required)
    if len(extra_cols)>0:
        logging.error(f'Unrecognized columns: {extra_cols}')
        has_error = True


    # loop over required columns and ensure they contain expected information
    missing_data = []
    no_data = []
    duplicate_data = []
    not_numeric = []
    for col in (file_info.required_cols + file_info.optional_cols):
        if col.name in col_names:
            # test for missing data
            if not col.nullable:
                if df[col.name].dropna().shape[0]<df[col.name].shape[0]:
                    missing_data.append(col.name)
            else:
                # these are nullable, so they are optional
                if df[col.name].dropna().shape[0]==0:
                    no_data.append(col.name)
            # test for unique values
            if col.unique:
                if len(set(df[col.name]))<df[col.name].shape[0]:
                    duplicate_data.append(col.name)
            # verify values are numeric
            if col.numeric:
                try:
                    pd.to_numeric(df[col.name], errors='raise')
                except Exception:
                    not_numeric.append(col.name)
    if len(missing_data)>0:
        logging.error(f'Columns with missing data: {missing_data}')
        has_error = True
    if len(no_data)>0:
        df = df.drop(columns=no_data)
        logging.warning(f'Columns with no data: {no_data}')
    if len(duplicate_data)>0:
        logging.error(f'Columns with duplicate entries: {duplicate_data}')
        has_error = True
    if len(not_numeric)>0:
        logging.error(f'Columns with non-numeric data: {not_numeric}')
        has_error = True

    invalid_values = []
    for col in (file_info.required_cols + file_info.optional_cols):
        if col.name in col_names:
            # check that values match defined valid values
            if col.valid_values:
                values_in_col = list(df[col.name].dropna())
                # convert values to numbers to do the comparison
                values_in_col_as_num = [_convert_to_number(x) for x in values_in_col]
                invalid_values = set(values_in_col_as_num) - set(col.valid_values)
                if len(invalid_values)>0:
                    logging.error(f"Invalid values in column \'{col.name}\': {invalid_values} not among {col.valid_values}")
                    has_error = True

    return None if has_error else df

def _convert_to_number(string):
    try:
        return int(string)
    except ValueError:
        try:
            return float(string)
        except ValueError:
            return string

def _clean_origins(df):
    if df is  None:
        return df
    # verify there are no negative populations
    num_negative = len(df.query('population < 0'))
    num_zero = len(df.query('population==0'))
    if num_negative>0:
        logging.warning(f'{num_negative} origins with population < 0 removed')
    if num_zero>0:
        logging.warning(f'{num_zero} origins with population = 0 removed')

    # remove origins with 0 population
    df = df.query('population > 0').reset_index(drop=True)
    if df.shape[0]==0:
        logging.error('There are no origins with positive population')
        return None
    
    return df


def build_dist_df(orig_df, dest_df, dist_lookup_df):
    '''return dataframe with: origin, destination, distance, population
    for the needed pairs (distances are read from the provided 
    distance csv file, which may have extra distances)
    '''
    dist_df = (
        orig_df
        .merge(dest_df, how='cross')
        .rename(columns={'id_x':'origin','id_y':'destination'})
        .merge(dist_lookup_df, on=['origin','destination'], how='left')
        [['origin','destination','population','distance']]
    )
    missing_distances = dist_df.query('distance.isna()')[['origin','destination']]
    if len(missing_distances)>0:
        logging.error(f'No distance data for {missing_distances}')
        return None
    
    return dist_df