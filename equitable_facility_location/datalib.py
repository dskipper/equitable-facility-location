import pandas as pd
from itertools import product
import numpy as np
from dataclasses import dataclass, field

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

# check if data file has the correct attributes
def check_data(path_to_csv, file_info):
    errors = []
    file_name = file_info.name
    df = pd.read_csv(path_to_csv)
    col_names = set(df.columns.values)

    # test if data has required columns
    required = {col.name for col in file_info.required_cols}
    missing_cols = required - col_names
    if len(missing_cols)>0:
        errors.append(f'Missing required columns: {missing_cols}')
    
    # test if there are unrecognized columns
    optional = {col.name for col in file_info.optional_cols}
    extra_cols = col_names - (optional | required)
    if len(extra_cols)>0:
        errors.append(f'Unrecognized columns: {extra_cols}')
    
    # exit if there are problems with existing columns
    if len(errors)>0:
        return errors

    # loop over required columns and ensure they contain expected information
    missing_data = []
    duplicate_data = []
    not_numeric = []
    invalid = []
    for col in (file_info.required_cols + file_info.optional_cols):
        if col.name in col_names:
            # test for missing data
            if not col.nullable:
                if df[col.name].dropna().shape[0]<df[col.name].shape[0]:
                    missing_data.append(col.name)
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
        errors.append(f'Columns with missing data: {missing_data}')
    if len(duplicate_data)>0:
        errors.append(f'Columns with duplicate entries: {duplicate_data}')
    if len(not_numeric)>0:
        errors.append(f'Columns with non-numeric data: {not_numeric}')

    invalid = []
    for col in (file_info.required_cols + file_info.optional_cols):
        if col.name in col_names:
            # check that values match defined valid values
            if col.valid_values:
                values_in_col = list(df[col.name].dropna())
                # convert values to numbers to do the comparison
                values_in_col_as_num = [convert_to_number(x) for x in values_in_col]
                invalid_values = set(values_in_col_as_num) - set(col.valid_values)
                if len(invalid_values)>0:
                    # convert values to strings to sort
                    invalid_values = sorted([str(x) for x in list(invalid_values)])
                    # convert back to numbers for displaying
                    invalid_values = [convert_to_number(x) for x in invalid_values]
                    errors.append(f"Invalid values in column \'{col.name}\': {invalid_values} not among {col.valid_values}")

    return errors

def convert_to_number(string):
    try:
        return int(string)
    except ValueError:
        try:
            return float(string)
        except ValueError:
            return string



def clean_origins(df):
    warnings = []
    errors = []

    # verify there are no negative populations
    num_negative = len(df.query('population < 0'))
    num_zero = len(df.query('population==0'))
    if num_negative>0:
        warnings.append(f'Warning: {num_negative} origins with population < 0 removed')
    if num_zero>0:
        warnings.append(f'Warning: {num_zero} origins with population = 0 removed')

    if len(warnings)>0:
        print(warnings)  # Dan: how do I handle this warning?

    # remove origins with 0 population
    num_ids = df['id'].count()
    df = df.query('population > 0').reset_index(drop=True)
    if df.shape[0]==0:
        errors.append('There are no origins with positive population')
        return errors # Dan: how do I handle this error?
    
    return df


def build_dist_df(orig_df, dest_df, dist_lookup_df):
    errors = []
    csv_name = 'distances csv'
    dist_df = (
        orig_df
        .merge(dest_df, how='cross')
        .rename(columns={'id_x':'origin','id_y':'destination'})
        .merge(dist_lookup_df, on=['origin','destination'], how='left')
        [['origin','destination','population','distance']]
    )
    missing_distances = dist_df.query('distance.isna()')[['origin','destination']]
    if len(missing_distances)>0:
        errors.append(f'No distance data for {missing_distances}')
        return errors
    
    return dist_df