import datetime
import folium
import pandas as pd
import geopandas as gpd
import ipywidgets as widgets
import plotly.graph_objects as go
import plotly.io as pio
from shapely.geometry import Point


#////////////////////////////////////////////////////////////////////////////////////////////////////////

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
    
    #temp_net_filtered.to_csv(netatmo_out_path + 'temp_Net_milan_%s-%s_filtered.csv' % (year, month), index=False)
    #reliability_df.to_csv(netatmo_out_path + 'Reliability_Index/stations_reliability_%s-%s.csv' % (year, month), index=False)
    
    return reliability_df, filtered_stations, removed_stations, temp_net_filtered

#////////////////////////////////////////////////////////////////////////////////////////////////////////

def plot_stations_reliability_map(selected_df, aoi_filepath='CMM.gpkg'):
    
    try:
        aoi_gdf = gpd.read_file(aoi_filepath)
    except Exception as e:
        print(f"Failed to read file {aoi_filepath}: {e}")
        return None

    # Create 'geometry' column as Point objects
    geometry_array = [Point(xy) for xy in zip(selected_df['long'], selected_df['lat'])]
    # Create a GeoDataFrame
    selected_gdf = gpd.GeoDataFrame(selected_df, geometry=geometry_array, crs='EPSG:4326')

    # Set up the base map
    m = folium.Map(
        location=[selected_gdf.geometry.y.mean(), selected_gdf.geometry.x.mean()],
        zoom_start=9,
        tiles='OpenStreetMap')

    folium.GeoJson(
        aoi_gdf,
        name='Area of Interest',
        style_function=lambda x: {'fillColor': 'SkyBlue', 'color': 'Blue', 'fillOpacity': 0, 'weight': 2}
    ).add_to(m)

    # Classify 'sens_reliability' into categories
    bins = [0, 0.25, 0.5, 0.75, 1]
    labels = ['0-0.25', '0.25-0.5', '0.5-0.75', '0.75-1']
    color_map = {
        '0-0.25': '#ff0000',
        '0.25-0.5': '#ffcc00',
        '0.5-0.75': '#ccff33',
        '0.75-1': '#33cc33'
    }
    selected_gdf['Reliability Class'] = pd.cut(selected_gdf['sens_reliability'], bins=bins, labels=labels, include_lowest=True)

    # Apply custom colors based on 'Reliability Class'
    for _, row in selected_gdf.iterrows():
        popup_text = f'Station: {row["module_id"]} ({row["city"]},{row["street"]})\nReliability:({row["sens_reliability"]:.2f})'
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=5,
            color=color_map[row['Reliability Class']],
            fill=True,
            fill_color=color_map[row['Reliability Class']],
            fill_opacity=0.7,
            popup= popup_text
            # popup=f'Reliability: {row["sens_reliability"]}'
        ).add_to(m)

    # Add a legend
    legend_html = '''
     <div style="position: fixed; 
                 bottom: 15px; right: 10px; width: 160px; height: 110px; 
                 border:2px solid black; background-color: white; z-index:9999; font-size:14px;
                 "&nbsp; <b>Reliability index</b><br>
                 &nbsp; <i style="background-color:#ff0000;">&nbsp;&nbsp;&nbsp;&nbsp;</i> unreliable <br>
                 &nbsp; <i style="background-color:#ffcc00;">&nbsp;&nbsp;&nbsp;&nbsp;</i> low (0.25-0.5) <br>
                 &nbsp; <i style="background-color:#ccff33;">&nbsp;&nbsp;&nbsp;&nbsp;</i> moderate (0.5-0.75) <br>
                 &nbsp; <i style="background-color:#33cc33;">&nbsp;&nbsp;&nbsp;&nbsp;</i> high (0.75-1.0)
              </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)

    return m

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function resamples the temperature column in a file DAILY and returns
# the (min, max, mean, median, std) values of that month
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def resample_df_daily(folder_path,year,month,file_type):
    # Read the CSV file
    files_path = (folder_path + f'temp_Net_milan_{year}-{month}_{file_type}.csv')
    df = pd.read_csv(files_path)
    
    # Extract relevant columns for sensors
    df1 = df[["device_id", "module_id", "lat", "long", "timezone", "country", "altitude", "city", "street", "geometry"]].drop_duplicates(subset="module_id", keep="first")
    
    # Convert 'time' column to datetime and set it as the index
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    
    # Group by module_id and date
    grouped = df.groupby(['module_id', df.index.date])

    # Resample temperature data
    daily_min_temp = grouped['Temperature'].resample('D').min()
    daily_max_temp = grouped['Temperature'].resample('D').max()
    daily_mean_temp = grouped['Temperature'].resample('D').mean()
    daily_median_temp = grouped['Temperature'].resample('D').median()
    daily_std_temp = grouped['Temperature'].resample('D').std()

    # Create a DataFrame with daily temperature statistics
    df2 = pd.DataFrame({
        'Min_Temp': daily_min_temp,
        'Mean': daily_mean_temp,
        'Median': daily_median_temp,
        'Max_Temp': daily_max_temp,
        'Std': daily_std_temp
    })
    df2.reset_index(inplace=True)
    df2.drop(columns=['level_1'], inplace=True)

    # Merge the DataFrames based on the common key column
    daily_stat = pd.merge(df2, df1, on='module_id', how='inner')

    # Reorder the columns
    daily_stat = daily_stat[['time', 'Min_Temp', 'Mean', 
                           'Median', 'Max_Temp', 'Std', 'device_id','module_id', 
                            'lat', 'long', 'timezone', 'country', 'altitude', 
                           'city', 'street', 'geometry']]
    
    # Create 'geometry' column as Point objects
    geometry_array = [Point(xy) for xy in zip(daily_stat['long'], daily_stat['lat'])]
    # Create a GeoDataFrame
    daily_stat_gdf = gpd.GeoDataFrame(daily_stat, geometry=geometry_array, crs='EPSG:4326')
    
    # Convert time column to string
    daily_stat_gdf['time'] = daily_stat_gdf['time'].astype(str)

    return daily_stat_gdf
    
#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function resamples the temperature column MONTHLY returning
# the (min, max, mean, median, std) values of that month
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def resample_df_montly(folder_path,year,month,file_type):
    # Read the CSV file
    files_path = (folder_path + f'temp_Net_milan_{year}-{month}_{file_type}.csv')
    df = pd.read_csv(files_path)
    
    # Extract relevant columns for sensors
    df1 = df[["device_id", "module_id", "lat", "long", "timezone", "country", "altitude", "city","street","geometry"]].drop_duplicates(subset="module_id", keep="first")
    
    # Convert 'time' column to datetime and set it as the index
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    
    # Group by module_id and date
    grouped = df.groupby(['module_id', pd.Grouper(freq='M')])

    # Resample temperature data
    monthly_min_temp = grouped['Temperature'].min()
    monthly_max_temp = grouped['Temperature'].max()
    monthly_mean_temp = grouped['Temperature'].mean()
    monthly_median_temp = grouped['Temperature'].median()
    monthly_std_temp = grouped['Temperature'].std()

    # Create a DataFrame with montly temperature statistics
    df2 = pd.DataFrame({
        'Min_Temp': monthly_min_temp,
        'Mean': monthly_mean_temp,
        'Median': monthly_median_temp,
        'Max_Temp': monthly_max_temp,
        'Std': monthly_std_temp
    })
    df2.reset_index(inplace=True)
    #df2.drop(columns=['level_1'], inplace=True)

    # Merge the DataFrames based on the common key column
    monthly_stat = pd.merge(df2, df1, on='module_id', how='inner')

    # Reorder the columns
    monthly_stat = monthly_stat[['time', 'Min_Temp', 'Mean', 
                           'Median', 'Max_Temp', 'Std', 'device_id','module_id', 
                            'lat', 'long', 'timezone', 'country', 'altitude', 
                           'city', 'street', 'geometry']]
        
    # Create 'geometry' column as Point objects
    geometry_array = [Point(xy) for xy in zip(monthly_stat['long'], monthly_stat['lat'])]
    # Create a GeoDataFrame
    monthly_stat_gdf = gpd.GeoDataFrame(monthly_stat, geometry=geometry_array, crs='EPSG:4326')
    
    # Convert time column to string
    monthly_stat_gdf['time'] = monthly_stat_gdf['time'].astype(str)

    return monthly_stat_gdf

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function resamples the temperature column MONTHLY concatenate all the monthly resampled dfs 
# returning the (min, max, mean, median, std) values of every month during the year
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def resample_df_annually(folder_path,year,file_type):
    
    ##Step_1: concatenate the montly_statistics data-frames to a single data frame df1
    # Create an empty DataFrame to store the resampled dataframes monthly
    dfs=[]

    if year == 2023:
        months = range(1, 10)  # January to September
    else:
        months = range(1, 13)  # All months
    
    for month in months:
        df = resample_df_montly(folder_path,year,month,file_type)
        globals()[f"df_{month}"] = df
        dfs.append(df)
        df1 = pd.concat(dfs, ignore_index=True)

    ##Step_2: create df2 filling the missing time gaps for all Netatmo stations
    
    columns = ['module_id','time', 'device_id', 'lat', 'long', 'timezone', 
               'country', 'altitude', 'city', 'street', 'geometry']
    df2 = pd.DataFrame(columns=columns)

    for month in months:
        df = globals()[f'df_{month}']
        df2 = pd.concat([df2, df[columns]], ignore_index=True)

    df2.drop_duplicates(subset='module_id', inplace=True)
    
    # Create a list of dates for each module_id
    dates = pd.date_range(start=f'{year}-01-31', end=f'{year}-12-31', freq='ME')
    dates = dates.strftime('%Y-%m-%d').tolist()  # Convert dates to string format
    
    # Create a dictionary to map module_id to dates
    dates_dict = {module_id: dates for module_id in df2['module_id'].unique()}
    
    # Create a new column 'time' and populate it with the corresponding dates
    df2['time'] = df2['module_id'].map(dates_dict)
    
    # Explode the 'time' column to separate rows for each date
    df2 = df2.explode('time')
    
    # Reset index
    df2.reset_index(drop=True, inplace=True)

    ##Step_3: Merge df1 and df2
    #perform a left join between the first dataframe (which contains all the rows) and the second dataframe
    #(which contains the temperature statistics).
    #This will ensure that all rows from the first dataframe are included in the final result,
    #and missing values in the second dataframe will be filled with NaN.
    
    
    # Convert 'time' column to datetime type in both dataframes
    if file_type == 'clip':
        df1['time'] = pd.to_datetime(df1['time']).dt.tz_localize(None)
    else:
       df1['time'] = pd.to_datetime(df1['time'])
    
    df2['time'] = pd.to_datetime(df2['time'])
    
    #perform a left join on 'module_id' and 'time' between the two dataframes with specified columns to merge.
    annual_stat = pd.merge(df2, df1[['module_id', 'time', 'Min_Temp', 'Mean', 
                                   'Median', 'Max_Temp', 'Std']], on=['module_id', 'time'], how='left')

    # Sort the dataframe by 'module_id' and 'time' for better readability
    annual_stat.sort_values(by=['module_id', 'time'], inplace=True)
    
    # Forward fill missing values for temperature statistics within each 'module_id'
    annual_stat[['Min_Temp', 'Mean', 'Median', 'Max_Temp', 'Std']] = annual_stat[['Min_Temp', 'Mean', 'Median', 'Max_Temp', 'Std']].fillna(0)
    
    #drop duplicate rows to keep only the unique rows in the final dataframe.
    annual_stat.drop_duplicates(subset=['module_id', 'time'], inplace=True)
    
    # Reorder the columns
    annual_stat = annual_stat[['time', 'Min_Temp', 'Mean', 
                           'Median', 'Max_Temp', 'Std', 'device_id','module_id',  
                           'lat', 'long', 'timezone', 'country', 'altitude', 
                           'city', 'street', 'geometry']]
    
    # Create 'geometry' column as Point objects
    geometry_array = [Point(xy) for xy in zip(annual_stat['long'], annual_stat['lat'])]
    # Create a GeoDataFrame
    annual_stat_gdf = gpd.GeoDataFrame(annual_stat, geometry=geometry_array, crs='EPSG:4326')
    
    # Convert time column to string
    annual_stat_gdf['time'] = annual_stat_gdf['time'].astype(str)

    
    return annual_stat_gdf

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function resamples the temperature column seasonly  returning
# the (min, max, mean, median, std) values of June, July, and August
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def resample_df_seasonly(folder_path,year,file_type):
    
    ##Step_1: concatenate the montly_statistics data-frames to a single data frame df1
    
    # Create an empty DataFrame to store the monthly resampled dataframes
    dfs=[]
    
    for month in range(6, 9):
        df = resample_df_montly(folder_path,year,month,file_type)
        globals()[f"df_{month}"] = df
        dfs.append(df)
        df1 = pd.concat(dfs, ignore_index=True)

    ##Step_2: create df2 filling the missing time gaps for all Netatmo stations
    
    columns = ['module_id','time', 'device_id', 'lat', 'long', 'timezone', 
               'country', 'altitude', 'city', 'street', 'geometry']
    df2 = pd.DataFrame(columns=columns)

    for month in range(6, 9):
        df = globals()[f'df_{month}']
        df2 = pd.concat([df2, df[columns]], ignore_index=True)

    df2.drop_duplicates(subset='module_id', inplace=True)
    
    # Create a list of dates for each module_id
    dates = pd.date_range(start=f'{year}-06-30', end=f'{year}-08-31', freq='ME')
    dates = dates.strftime('%Y-%m-%d').tolist()  # Convert dates to string format
    
    # Create a dictionary to map module_id to dates
    dates_dict = {module_id: dates for module_id in df2['module_id'].unique()}
    
    # Create a new column 'time' and populate it with the corresponding dates
    df2['time'] = df2['module_id'].map(dates_dict)
    
    # Explode the 'time' column to separate rows for each date
    df2 = df2.explode('time')
    
    # Reset index
    df2.reset_index(drop=True, inplace=True)

    ##Step_3: Merge df1 and df2
    #perform a left join between the first dataframe (which contains all the rows) and the second dataframe
    #(which contains the temperature statistics).
    #This will ensure that all rows from the first dataframe are included in the final result,
    #and missing values in the second dataframe will be filled with NaN.
    
    
    # Convert 'time' column to datetime type in both dataframes
    if file_type == 'clip':
        df1['time'] = pd.to_datetime(df1['time']).dt.tz_localize(None)
    else:
        df1['time'] = pd.to_datetime(df1['time'])

    
    df2['time'] = pd.to_datetime(df2['time'])
    
    #perform a left join on 'module_id' and 'time' between the two dataframes with specified columns to merge.
    summer_stat = pd.merge(df2, df1[['module_id', 'time', 'Min_Temp', 'Mean', 
                                   'Median', 'Max_Temp', 'Std']], on=['module_id', 'time'], how='left')

    # Sort the dataframe by 'module_id' and 'time' for better readability
    summer_stat.sort_values(by=['module_id', 'time'], inplace=True)
    
    # Forward fill missing values for temperature statistics within each 'module_id'
    summer_stat[['Min_Temp', 'Mean', 'Median', 'Max_Temp', 'Std']] = summer_stat[['Min_Temp', 'Mean', 'Median', 'Max_Temp', 'Std']].fillna(0)
    
    #drop duplicate rows to keep only the unique rows in the final dataframe.
    summer_stat.drop_duplicates(subset=['module_id', 'time'], inplace=True)
    
    # Reorder the columns
    summer_stat = summer_stat[['time', 'Min_Temp', 'Mean', 
                           'Median', 'Max_Temp', 'Std', 'device_id', 'module_id',  
                           'lat', 'long', 'timezone', 'country', 'altitude', 
                           'city', 'street', 'geometry']]
    
    # Create 'geometry' column as Point objects
    geometry_array = [Point(xy) for xy in zip(summer_stat['long'], summer_stat['lat'])]
    # Create a GeoDataFrame
    summer_stat_gdf = gpd.GeoDataFrame(summer_stat, geometry=geometry_array, crs='EPSG:4326')
    
    # Convert time column to string
    summer_stat_gdf['time'] = summer_stat_gdf['time'].astype(str)

    
    return summer_stat_gdf

##################################################################################################################
##################################################################################################################

  
#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function creates a date dropdown
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def create_date_dropdown(dataframe):
    # Group by 'time' column
    dates = dataframe.groupby('time')

    # Create separate DataFrames for each date
    separate_dataframes = {name: date for name, date in dates}
    
    # Get a list of unique dates
    day_w = list(separate_dataframes.keys())

    # Create a dropdown widget
    date_dropdown = widgets.Dropdown(
        options=day_w,
        description='Select date:',
    )

    return date_dropdown, separate_dataframes

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function creates stations dropdown
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def create_sensors_dropdown(dataframe):
    # Group by 'module_id' column
    sensors = dataframe.groupby('module_id')
    # Create separate DataFrames for each station
    separate_dataframes = {name: sensor for name, sensor in sensors}
    
    # Combine 'city' and 'street' for dropdown options
    #sensor_names = dataframe.apply(lambda x: f"{x['city']}, {x['street']}", axis=1).unique().tolist()
    
    # Get a list of unique stations
    sensor_names = list(separate_dataframes.keys())
    
    # Create a dropdown widget
    sensor_dropdown = widgets.Dropdown(
        options=sensor_names,
        description='Select Sensor:',
    )
    sensor_dropdown
    return sensor_dropdown, separate_dataframes

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function creates a map displaying the median temperature values
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def plot_median_temp_map(selected_gdf):
    # Create 'geometry' column as Point objects
    #geometry_array = [Point(xy) for xy in zip(selected_df['long'], selected_df['lat'])]
    # Create a GeoDataFrame
    #selected_gdf = gpd.GeoDataFrame(selected_df, geometry=geometry_array, crs='EPSG:4326')

    aoi_gdf = gpd.read_file('CMM.gpkg')
    m = aoi_gdf.explore(
        marker_kwds=dict(radius=10, fill=True),
        tooltip_kwds=dict(labels=False),
        tooltip=False,
        popup=False,
        highlight=False,
        name="cmm"
    )

    selected_gdf.explore(
        m=m,
        column= 'Median',
        tooltip=['module_id','city', 'street','Min_Temp', 'Mean', 'Median', 'Max_Temp'],
        popup=True,
        tiles="CartoDB positron",
        #marker_kwds=dict(radius=4, fill=False, color='red'),
        marker_kwds=dict(radius=4, fill=True, color='red_color_ramp'),
        cmap='Spectral_r'
    )
    
    # Add north arrow
    north_arrow_html = '''
    <div style="position: fixed; top: 50px; right: 35px; width: 52px; height: 70px; 
                background-color: white; border:2px solid black; z-index:9999; font-size:15px;">
        <img src="https://th.bing.com/th/id/R.c66b4aa98a0cbcf2c9c62da5819e528a?rik=hnWDHcMoO8Hnhw&riu=http%3a%2f%2fpluspng.com%2fimg-png%2ffree-png-north-arrow-big-image-png-1659.png&ehk=KTDoWmlfwvZGkF3%2f3F9JY1ltV6DkLkrkHog%2fpXQiyqc%3d&risl=&pid=ImgRaw&r=0" 
             style="width:50px; height:60px;">
    </div>
    '''
    m.get_root().html.add_child(folium.Element(north_arrow_html))

    return m

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function creates a daily statistics plot
#////////////////////////////////////////////////////////////////////////////////////////////////////////
   
def plot_daily_statistics(df, date_dropdown):
    # Convert the data to plotly format
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Min_Temp'], mode='lines', name='Min Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Max_Temp'], mode='lines', name='Max Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Mean'], mode='lines', name='Mean Temperature'))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Median'], mode='lines', name='Median Temperature'))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Std'], mode='lines',name='Standard Deviation',
                             showlegend=False,line=dict(color='rgba(0,60,100,0.8)')))

    # Add std as shaded area
    fig.add_trace(go.Scatter(
        x=df['module_id'],
        y=df['Mean'] + df['Std'],
        mode='lines',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=df['module_id'],
        y=df['Mean'] - df['Std'],
        fill='tonexty',
        fillcolor='rgba(0,60,100,0.8)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Standard Deviation',
        hoverinfo='skip',
    ))

    # Update layout for better interactivity
    fig.update_layout(
        title=f'Temp-values recorded by Netatmo stations on {date_dropdown.value}:',
        xaxis_title='module_id',
        yaxis_title='Temperature',
        hovermode='x',
        template='plotly_dark', 
        #template='seaborn',
        #template='ggplot2',
    )

    return fig

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function creates a monthly statistics plot
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def plot_montly_statistics(df,month,year):
    # Convert the data to plotly format
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Min_Temp'], mode='lines', name='Min Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Max_Temp'], mode='lines', name='Max Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Mean'], mode='lines', name='Mean Temperature'))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Median'], mode='lines', name='Median Temperature'))
    fig.add_trace(go.Scatter(x=df['module_id'], y=df['Std'], mode='lines',name='Standard Deviation',
                             showlegend=False,line=dict(color='rgba(0,60,100,0.8)')))

    # Add std as shaded area
    fig.add_trace(go.Scatter(
        x=df['module_id'],
        y=df['Mean'] + df['Std'],
        mode='lines',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=df['module_id'],
        y=df['Mean'] - df['Std'],
        fill='tonexty',
        fillcolor='rgba(0,60,100,0.8)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Standard Deviation',
        hoverinfo='skip',
    ))

    # Update layout for better interactivity
    fig.update_layout(
        title=f'Temp-values recorded by Netatmo stations on: {month}/{year}',
        xaxis_title='module_id',
        yaxis_title='Temperature',
        hovermode='x',
        template='plotly_dark', 
        #template='seaborn',
        #template='ggplot2',
    )

    return fig

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function plots a selected station time series monthly
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def plot_time_series_m(df, sensor_dropdown, month, year):
    # Convert the data to plotly format
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['time'], y=df['Min_Temp'], mode='lines', name='Min Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Max_Temp'], mode='lines', name='Max Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Mean'], mode='lines', name='Mean Temperature'))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Median'], mode='lines', name='Median Temperature'))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Std'], mode='lines',name='Standard Deviation',
                             showlegend=False,line=dict(color='rgba(0,60,100,0.8)')))

    # Add std as shaded area
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['Mean'] + df['Std'],
        mode='lines',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['Mean'] - df['Std'],
        fill='tonexty',
        fillcolor='rgba(0,60,100,0.8)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Standard Deviation',
        hoverinfo='skip',
    ))

    # Update layout for better interactivity
    fig.update_layout(
        title=f"Netatmo station: {df['city'].iloc[0]},{df['street'].iloc[0]} time series :{month}/{year}",
        xaxis_title='time',
        yaxis_title='Temperature',
        hovermode='x',
        template='plotly_dark', 
        #template='seaborn',
        #template='ggplot2',
    )

    return fig

#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function plots a selected station time series yearly
#////////////////////////////////////////////////////////////////////////////////////////////////////////

def plot_time_series(df, sensor_dropdown, year):
    # Convert the data to plotly format
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['time'], y=df['Min_Temp'], mode='lines', name='Min Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Max_Temp'], mode='lines', name='Max Temperature', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Mean'], mode='lines', name='Mean Temperature'))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Median'], mode='lines', name='Median Temperature'))
    fig.add_trace(go.Scatter(x=df['time'], y=df['Std'], mode='lines',name='Standard Deviation',
                             showlegend=False,line=dict(color='rgba(0,60,100,0.8)')))

    # Add std as shaded area
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['Mean'] + df['Std'],
        mode='lines',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['Mean'] - df['Std'],
        fill='tonexty',
        fillcolor='rgba(0,60,100,0.8)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Standard Deviation',
        hoverinfo='skip',
    ))

    # Update layout for better interactivity
    fig.update_layout(
        title=f"Netatmo station: {df['city'].iloc[0]},{df['street'].iloc[0]} time series -{year}",
        xaxis_title='time',
        yaxis_title='Temperature',
        hovermode='x',
        template='plotly_dark', 
        #template='seaborn',
        #template='ggplot2',
    )

    return fig
#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function plots a histogram of the median temperature
#////////////////////////////////////////////////////////////////////////////////////////////////////////     

import seaborn as sns
import matplotlib.pyplot as plt
import calendar

def plot_histogram_clip(df, month, year):
    # Assuming month and year variables are defined
    month_name = calendar.month_name[month]
    
    # Create the figure for the histogram plot
    fig, ax1 = plt.subplots(figsize=(8, 5))
    # Plot the histogram
    sns.histplot(df['Median'], bins=20, kde=True, ax=ax1)
    ax1.set_xlabel(f'Median temperature values {month_name}/{year}')
    ax1.set_ylabel('freqency')
    
    # Adjust layout to fit the plot
    plt.tight_layout()

    # Save the plot as an image (e.g., PNG, JPG, PDF)
    #hist_path = 'D:/Netatmo_data_analysis/figs/median_temp/histograms/'
    #plt.savefig(hist_path + f'hist_{year}_{month}_clip.png')
    
    # Show the plot
    plt.show()

    
    
    return plt


def plot_histogram_clean(df, month, year):
    # Assuming month and year variables are defined
    month_name = calendar.month_name[month]
    
    # Create the figure for the histogram plot
    fig, ax1 = plt.subplots(figsize=(8, 5))
    # Plot the histogram
    sns.histplot(df['Median'], bins=20, kde=True, ax=ax1)
    ax1.set_xlabel(f'Median temperature values {month_name}/{year}')
    ax1.set_ylabel('freqency')
    
    # Adjust layout to fit the plot
    plt.tight_layout()

    # Save the plot as an image (e.g., PNG, JPG, PDF)
    #hist_path = 'D:/Netatmo_data_analysis/figs/median_temp/histograms/'
    #plt.savefig(hist_path + f'hist_{year}_{month}_clean.png')
    
    # Show the plot
    plt.show()

    
    
    return plt
#////////////////////////////////////////////////////////////////////////////////////////////////////////
# this function plots a selected station time series yearly
#////////////////////////////////////////////////////////////////////////////////////////////////////////   

def create_monthly_Box_plot(df, month, year):
    fig = go.Figure()

    fig.add_trace(go.Box(x=df['module_id'], y=df['Min_Temp'], name='Min Temperature'))
    fig.add_trace(go.Box(x=df['module_id'], y=df['Max_Temp'], name='Max Temperature'))
    fig.add_trace(go.Box(x=df['module_id'], y=df['Mean'], name='Mean Temperature'))
    fig.add_trace(go.Box(x=df['module_id'], y=df['Median'], name='Median Temperature'))

    fig.update_layout(
        title=f'Temp-values recorded by Netatmo_Stations on: {month}_{year}',
        xaxis_title='module_id',
        yaxis_title='Temperature',
        hovermode='x',
        template='plotly_dark', 
    )

    return fig

# Example usage:
# fig = create_monthly_plot(df, "January", 2024)
# fig.show()

