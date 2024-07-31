import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import datetime
from datetime import timedelta

# ----------------------------------------------------------

def compute_corr(year, month, temp_net_df, temp_arpa_df_original, netatmo_out_path):
    pd.set_option('mode.chained_assignment', None)

    module_stations = temp_net_df.module_id.unique()

    # Not necessary as it is not read from csv
    # temp_arpa_df['datetime'] = pd.to_datetime(temp_arpa_df['datetime'], format="%Y-%m-%d %H:%M:%S")

    # copy to avoid modification of the original virtual station
    temp_arpa_df = temp_arpa_df_original.copy(deep=True)
    temp_arpa_df['datetime'] = temp_arpa_df['datetime'] + timedelta(minutes=30)
    temp_arpa_df.set_index('datetime', inplace=True)

    # Compute the correlation for each station
    corr_dict = {
        'module_id': [],
        'lat': [],
        'long': [],
        'year': [],
        'pearson_coef': []
    }

    for station in module_stations:
        if not pd.isna(station):
            # Filter the df to have only the measures of the module
            temp_net_df_mod = temp_net_df[(temp_net_df['module_id'] == station)]
            lat_module = temp_net_df_mod['lat'].iloc[0]
            long_module = temp_net_df_mod['long'].iloc[0]
            temp_net_df_station = temp_net_df_mod[
                (temp_net_df_mod['lat'] == lat_module) & (temp_net_df_mod['long'] == long_module)]

            # Modify time to be comparable with ARPA
            temp_net_df_station['time'] = pd.to_datetime(temp_net_df_station['time'], format="%Y-%m-%d %H:%M:%S+00:00")
            temp_net_df_station['time'] = temp_net_df_station['time'].dt.tz_localize(None)
            temp_net_df_station = temp_net_df_station.drop_duplicates()
            temp_net_df_station = temp_net_df_station.drop_duplicates()
            temp_net_df_station.set_index('time', inplace=True)

            # Concat the two CSV to match the corresponding hours
            concat_df = pd.concat([temp_arpa_df, temp_net_df_station], join='inner', axis=1)

            correlation = concat_df['Temperature'].corr(concat_df['avgTemp'])

            corr_dict['module_id'].append(station)
            corr_dict['lat'].append(lat_module)
            corr_dict['long'].append(long_module)
            corr_dict['year'].append(year)
            corr_dict['pearson_coef'].append(correlation)

    df_corr = pd.DataFrame(corr_dict)

    # Put the data into a CSV file
    corr_csv = df_corr.to_csv(netatmo_out_path + 'corr_ARPA_netatmo_%s-%s.csv' % (year, month), index=False)
    return df_corr

# ----------------------------------------------------------

def remove_low_corr(year, month, netatmo_out_path, corr_df, temp_net_df):
    pd.set_option('mode.chained_assignment', None)

    # Variable to store the removals at different steps
    removals = {
        'initial': [],
        'high_corr': [],
        'removed': [],
    }

    # Open the Netatmo CSV file containing the correlations
    # corr_df = pd.read_csv('corr_ARPA_netatmo_csv_%s.csv' % (year), skiprows=0)

    # Filter to obtain the module_id of stations with corr >= 0.6
    high_corr_df = corr_df[(corr_df['pearson_coef'] >= 0.6)]
    high_corr_modules = high_corr_df.module_id.unique()

    # Open the Netatmo CSV file containing the hourly measures
    # temp_Net_df = pd.read_csv('temp_Net_milan_clip_%s.csv' % (year), skiprows=0)

    removals['initial'].append(len(temp_net_df))

    # Filter to keep only the stations with corr >= 0.6
    temp_net_high_corr_df = temp_net_df[(temp_net_df.module_id.isin(high_corr_modules))]
    removals['high_corr'].append(len(temp_net_high_corr_df))

    # Put cleaned data into a csv
    removed = (1 - len(temp_net_high_corr_df) / len(temp_net_df)) * 100
    removals['removed'].append(removed)

    df_removals = pd.DataFrame(removals)
    
    temp_net_high_corr_df.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_high_corr.csv' % (year, month), index=False)
    # Put also the removals into a csv
    df_removals.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_correlation_stats.csv' % (year, month), index=False)

    return temp_net_high_corr_df, df_removals

# ----------------------------------------------------------

def remove_unrealistic_values(year, month, netatmo_out_path, temp_net_df, temp_arpa_df):
    pd.set_option('mode.chained_assignment', None)

    module_stations = temp_net_df.module_id.unique()
    # Remove value out of range

    # Get the maximum and minimum values of ARPA, add/remove 2 degrees for possible fluctuations (UHI effect...)
    maximum = temp_arpa_df['maxTemp'].max() + 2
    minimum = temp_arpa_df['minTemp'].min() - 2

    # To store the stats of removals
    removals_out_min_max = {
        'initial': [],
        'in_range': [],
        'removed': [],
        'module_id': [],
        'lat': [],
        'long': [],
        'year': [],
    }

    # To store cleaned dataframes
    all_df = []

    # For every station, remove value out of range
    for station in module_stations:
        if not pd.isna(station):
            # Filter the df to have only the measures of the station
            temp_net_df_mod = temp_net_df[(temp_net_df['module_id'] == station)]
            lat_module = temp_net_df_mod['lat'].iloc[0]
            long_module = temp_net_df_mod['long'].iloc[0]
            temp_net_df_station = temp_net_df_mod[
                (temp_net_df_mod['lat'] == lat_module) & (temp_net_df_mod['long'] == long_module)]
            removals_out_min_max['initial'].append(len(temp_net_df_station))

            # Filter the df to have only the measures in the range
            temp_net_df_in_range = temp_net_df_station[
                (temp_net_df_station['Temperature'] > minimum) & (temp_net_df_station['Temperature'] < maximum)]
            removals_out_min_max['in_range'].append(len(temp_net_df_in_range))
            removals_out_min_max['removed'].append((1 - len(temp_net_df_in_range) / len(temp_net_df_station)) * 100)
            all_df.append(temp_net_df_in_range)

            # Add data of the station
            removals_out_min_max['module_id'].append(station)
            removals_out_min_max['lat'].append(lat_module)
            removals_out_min_max['long'].append(long_module)
            removals_out_min_max['year'].append(year)

    df_concat = pd.concat(all_df)
    df_stats_removals = pd.DataFrame(removals_out_min_max)
    
    df_concat.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_realistic.csv' % (year, month), index=False)
    # Put also the removals into a csv
    df_stats_removals.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_unrealistic_stats.csv' % (year, month), index=False)

    return df_concat, df_stats_removals

# ----------------------------------------------------------

def remove_biased_series(year, month, netatmo_out_path, temp_net_df, temp_arpa_df_original):
    pd.set_option('mode.chained_assignment', None)

    # Variable to store the removals at different steps
    removals_outliers_ref_arpa = {
        'initial': [],
        'cleaned': []
    }

    removals_outliers_ref_arpa['initial'].append(len(temp_net_df))
    module_stations = temp_net_df.module_id.unique()

    # copy to avoid modification of the original virtual station
    temp_arpa_df = temp_arpa_df_original.copy(deep=True)

    # Modify the time of 30min to be able to match with Netatmo measures
    temp_arpa_df['datetime'] = temp_arpa_df['datetime'] + timedelta(minutes=30)

    # Variables for the cleaning
    temp_net_df_cleaned = []
    stats_cleaning = {
        'module_id': [],
        'lat': [],
        'long': [],
        'year': [],
        'removed_values': []
    }

    # For every station, compare each hourly measure with the virtual hourly mean
    for station in module_stations:
        nb_measures = 0
        removed_mesures = 0

        if not pd.isna(station):

            # Filter the df to have only the measures of the station
            temp_net_df_mod = temp_net_df[(temp_net_df['module_id'] == station)]
            lat_module = temp_net_df_mod['lat'].iloc[0]
            long_module = temp_net_df_mod['long'].iloc[0]
            temp_net_df_station = temp_net_df_mod[
                (temp_net_df_mod['lat'] == lat_module) & (temp_net_df_mod['long'] == long_module)]

            # Modify time to be comparable with ARPA
            temp_net_df_station['time'] = pd.to_datetime(temp_net_df_station['time'], format="%Y-%m-%d %H:%M:%S+00:00")
            temp_net_df_station['time'] = temp_net_df_station['time'].dt.tz_localize(None)
            temp_net_df_station = temp_net_df_station.drop_duplicates()

            temp_net_df_station_cleaned = temp_net_df_station.copy(deep=True)

            # Compare the station measure with the ARPA values
            for idx, row in temp_net_df_station.iterrows():
                nb_measures += 1
                net_value = row['Temperature']
                arpa_row = temp_arpa_df[(temp_arpa_df['datetime'] == row['time'])]
                arpa_value = arpa_row['avgTemp'].values[0]
                arpa_std = arpa_row['stdev'].values[0]
                upper_bound = arpa_value + 3 * arpa_std
                lower_bound = arpa_value - 3 * arpa_std

                if (net_value > upper_bound) or (net_value < lower_bound):
                    # Remove the measure
                    temp_net_df_station_cleaned = temp_net_df_station_cleaned.drop(idx)
                    # Count the nb of removed measures
                    removed_mesures += 1

            # For the final cleaned dataframe
            temp_net_df_cleaned.append(temp_net_df_station_cleaned)

            # For the stats
            stats_cleaning['module_id'].append(station)
            stats_cleaning['lat'].append(temp_net_df_station['lat'].values[0])
            stats_cleaning['long'].append(temp_net_df_station['long'].values[0])
            stats_cleaning['year'].append(year)

            if nb_measures > 0:
                percentage_removed = removed_mesures / nb_measures * 100
            else:
                percentage_removed = 0
            stats_cleaning['removed_values'].append(percentage_removed)

    tot_cleaned_df = pd.concat(temp_net_df_cleaned)
    removals_outliers_ref_arpa['cleaned'].append(len(tot_cleaned_df))
    df_stats = pd.DataFrame(stats_cleaning)
    df_removals = pd.DataFrame(removals_outliers_ref_arpa)
    
    #tot_cleaned_df.reset_index(drop=True, inplace=True)  # Reset index to ensure monotonicity
    
    tot_cleaned_df.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_unbiased.csv' % (year, month), index=False)
    # Put also the removals into a csv
    df_removals.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_biased_tot_stats.csv' % (year, month), index=False)
    df_stats.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_biased_station_stats.csv' % (year, month), index=False)
    

    return tot_cleaned_df, df_removals, df_stats

# ----------------------------------------------------------

# Warning: This function modifies the index of the original dataframe
def remove_local_outliers(year, month, netatmo_out_path, temp_net_df):
    pd.set_option('mode.chained_assignment', None)

    temp_net_df.set_index('time', inplace=True)
    module_stations = temp_net_df.module_id.unique()

    temp_net_df_rm = []

    # For every station, apply the rolling mean
    for station in module_stations:

        if not pd.isna(station):
            # Filter the df to have only the measures of the station
            temp_net_df_mod = temp_net_df[(temp_net_df['module_id'] == station)]
            lat_module = temp_net_df_mod['lat'].iloc[0]
            long_module = temp_net_df_mod['long'].iloc[0]
            temp_net_df_station = temp_net_df_mod[
                (temp_net_df_mod['lat'] == lat_module) & (temp_net_df_mod['long'] == long_module)]

            # Apply th RM with 2 hours window
            rm_temperature = temp_net_df_station.Temperature.rolling('3h', min_periods=1).mean()

            # Replace the temperatures with the new ones
            modified_df = temp_net_df_station.copy(deep=True)
            modified_df['Temperature'] = rm_temperature
            temp_net_df_rm.append(modified_df)

    total_df = pd.concat(temp_net_df_rm)
    # The index is datetime
    
    #reset the index
    total_df.reset_index(inplace=True)
    #total_df.drop(columns=['level_1'], inplace=True)
    
    
    total_df.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_clean.csv' % (year, month), index=False)

    return total_df

# --------------------------------------------------------------------------------------------
#Add a further step of cleaning based on the reliability index
# --------------------------------------------------------------------------------------------

def remove_unreliable_stations(temp_net_df, temp_net_cleaned, netatmo_out_path, year, month):
    columns = ['module_id', 'device_id', 'lat', 'long', 'timezone', 'country', 'altitude',
               'city', 'street', 'geometry']

    df1_n_obs = temp_net_df.groupby('module_id').size().reset_index(name='n.obs(original)')
    df1 = pd.merge(df1_n_obs, temp_net_df.drop_duplicates('module_id')[columns], on='module_id', how='left')
    
    df2_n_obs = temp_net_cleaned.groupby('module_id').size().reset_index(name='n.obs(cleaned)')
    df2 = pd.merge(df2_n_obs, temp_net_cleaned.drop_duplicates('module_id')[columns], on='module_id', how='left')
    
    # First, merge only the specified column from df1 to df2 based on the common key 'module_id'
    merged_columns = pd.merge(df1[['module_id','n.obs(original)']], df2[['module_id']], on='module_id', how='left')
    
    # Merge the merged_column back to df2 based on the common key 'module_id'
    reliability_df = pd.merge(df2, merged_columns, on='module_id', how='left')
    
    reliability_df['n.obs(removed)'] = reliability_df['n.obs(original)']-reliability_df['n.obs(cleaned)']
    reliability_df['(r_percentage)'] = reliability_df['n.obs(removed)']/reliability_df['n.obs(original)']
    reliability_df['sens_reliability'] = reliability_df['n.obs(cleaned)'] / reliability_df['n.obs(original)']
    reliability_df = reliability_df.fillna(0)
    
    # Reorder the columns
    reliability_df = reliability_df[['module_id', 'n.obs(original)', 'n.obs(cleaned)', 'n.obs(removed)', '(r_percentage)',
                                     'sens_reliability', 'device_id', 'lat', 'long', 'timezone', 'country', 'altitude', 'city', 
                                     'street', 'geometry']]
    
    # Filter df1 based on sens_reliability
    filtered_stations = reliability_df[reliability_df['sens_reliability'] >= 0.5]
    removed_stations = reliability_df[reliability_df['sens_reliability'] <= 0.5]
    filtered_stations.reset_index(drop=True, inplace=True)
    removed_stations.reset_index(drop=True, inplace=True)
    
    # Get the list of module IDs with reliability >= 0.5
    reliable_stations = filtered_stations['module_id'].tolist()
    
    # Filter df2 based on reliable_module_ids
    temp_net_filtered = temp_net_cleaned[temp_net_cleaned['module_id'].isin(reliable_stations)]
    temp_net_filtered.reset_index(drop=True, inplace=True)
    
    temp_net_filtered.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_filtered.csv' % (year, month), index=False)
    reliability_df.to_csv(netatmo_out_path + 'Reliability_Index\stations_reliability_%s-%s.csv' % (year, month), index=False)
    return reliability_df, filtered_stations, removed_stations, temp_net_filtered

# ------------------------------------------------------------------------------------------------------------
# Function to clean the data for affected module_ids by removing duplicates and intervals less than one hour
# ------------------------------------------------------------------------------------------------------------

def remove_irregularity_in_dataset(data , year, month):
    cleaned_data = []

    # Iterate over each module_id
    for module_id in data['module_id'].unique():
        module_data = data[data['module_id'] == module_id]

        # Remove duplicate timestamps by keeping the first occurrence
        module_data = module_data.drop_duplicates(subset=['time'])
        module_data['time'] = pd.to_datetime(module_data['time'])
        # Sort by time to ensure correct order
        module_data = module_data.sort_values(by='time')
        # Set the time column as the index
        module_data.set_index('time', inplace=True)
        # Calculate the time differences between consecutive rows
        module_data['time_diff'] = module_data.index.to_series().diff().dt.total_seconds() / 3600
        # Remove rows with time differences less than one hour
        module_data = module_data[module_data['time_diff'].isna() | (module_data['time_diff'] >= 1)]
        # Drop the time_diff column
        module_data = module_data.drop(columns=['time_diff'])
        # Reset the index
        module_data.reset_index(inplace=True)
        cleaned_data.append(module_data)
    # Concatenate all cleaned module data
    total_cleaned_data = pd.concat(cleaned_data)
    total_cleaned_data.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_clip.csv' % (year, month), index=False)
    return total_cleaned_data
