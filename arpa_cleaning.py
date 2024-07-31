import pandas as pd
import datetime

# ----------------------------------------------------------

def remove_outliers(year, start_month, end_month, temp_df, arpa_out_path):

    pd.set_option('mode.chained_assignment', None)

    # Detect for each month if outliers are present and remove them
    # Method used: Outliers = Observations with z-scores > 3 or < -3

    cleaned_df = []

    for m in range(start_month, end_month + 1):
        if m < 9:
            date_start_str = str(year) + '-0' + str(m) + '-01 00:00:00'
            date_end_str = str(year) + '-0' + str(m + 1) + '-01 00:00:00'
        elif m == 9:
            date_start_str = str(year) + '-0' + str(m) + '-01 00:00:00'
            date_end_str = str(year) + '-' + str(m + 1) + '-01 00:00:00'
        elif m != 12:
            date_start_str = str(year) + '-' + str(m) + '-01 00:00:00'
            date_end_str = str(year) + '-' + str(m + 1) + '-01 00:00:00'
        else:
            date_start_str = str(year) + '-' + str(m) + '-01 00:00:00'
            date_end_str = str(year + 1) + '-01-01 00:00:00'

        date_time_start = datetime.datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S")
        date_time_end = datetime.datetime.strptime(date_end_str, "%Y-%m-%d %H:%M:%S")

        # Get only the values in this range of time for all the stations
        temp_df['Data'] = pd.to_datetime(temp_df['Data'], format="%d/%m/%Y %H:%M:%S")
        temp_df_fil1 = temp_df[(temp_df['Data'] < date_time_end)]
        temp_df_fil2 = temp_df_fil1[(temp_df_fil1['Data'] > date_time_start)]

        # find absolute value of z-score for each observation
        mean = temp_df_fil2['Valore'].mean()
        stdev = temp_df_fil2['Valore'].std()

        temp_df_fil2['zscore'] = (temp_df_fil2.Valore - mean) / stdev

        # only keep rows in dataframe with all z-scores less than absolute value of 3
        data_clean = temp_df_fil2[(temp_df_fil2.zscore > -3) & (temp_df_fil2.zscore < 3)]

        cleaned_df.append(data_clean)

    tot_cleaned_df = pd.concat(cleaned_df)

    # Put the data into a CSV file
    ARPA_cleaned_csv = tot_cleaned_df.to_csv(arpa_out_path + 'ARPA_clean_%s-%s.csv' % (year, start_month), index=False)

    return tot_cleaned_df


# ----------------------------------------------------------

def create_virtual_station(year, start_month, end_month, temp_df, arpa_out_path):
    pd.set_option('mode.chained_assignment', None)

    # Compute for each date the mean and standard deviation of all the stations

    # New dictionary to store the hourly average
    temp_dict = {'datetime': [],
                 'avgTemp': [],
                 'median': [],
                 'minTemp': [],
                 'maxTemp': [],
                 'stdev': [],
                 #'madev': [],
                 'nb_measures': []}

    for m in range(start_month, end_month + 1):
        print(m)
        print("\n")
        if m in [1, 3, 5, 7, 8, 10, 12]:
            nb_days = 31

        # Be careful with the leap years: 2012, 2016, 2020
        elif m == 2:
            if year == 2016 or year == 2020 or year == 2012 or year == 2024:
                nb_days = 29
            else:
                nb_days = 28

        else:
            nb_days = 30

        for d in range(1, nb_days + 1):

            for h in range(0, 24):
                # Start time for the measures
                start = str(year) + '-' + str(m) + '-' + str(d) + ' ' + str(h) + ':00:00'
                date_time_start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")

                # End time: adding one hour to the start
                time_change = datetime.timedelta(minutes=60)
                date_time_end = date_time_start + time_change

                # Get only the values in this range of time for all the stations
                temp_df['Data'] = pd.to_datetime(temp_df['Data'], format="%Y-%m-%d %H:%M:%S")
                temp_df_fil1 = temp_df[(temp_df['Data'] < date_time_end)]
                temp_df_fil2 = temp_df_fil1[(temp_df_fil1['Data'] > date_time_start)]

                mean = temp_df_fil2['Valore'].mean()
                temp_dict['avgTemp'].append(round(mean, 2))
                median = temp_df_fil2['Valore'].median()
                temp_dict['median'].append(round(median, 2))
                temp_dict['minTemp'].append(temp_df_fil2['Valore'].min())
                temp_dict['maxTemp'].append(temp_df_fil2['Valore'].max())
                stdev = temp_df_fil2['Valore'].std()
                temp_dict['stdev'].append(round(stdev, 3))
                #madev = temp_df_fil2['Valore'].mad()
                #temp_dict['madev'].append(round(madev, 3))
                temp_dict['datetime'].append(date_time_start)
                temp_dict['nb_measures'].append(len(temp_df_fil2))

    virtual_station = pd.DataFrame(temp_dict)

    # Put the data into a CSV file
    milan_csv_data = temp_df.to_csv(arpa_out_path + 'ARPA_virtual_station_%s-%s.csv' % (year, start_month), index=False)

    return virtual_station
