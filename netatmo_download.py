import patatmo
from patatmo.api.errors import ApiResponseError
from datetime import datetime, timezone
from dotenv import load_dotenv
import os 
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import time

# ----------------------------------------------------------------------


def get_measure_by_month_to_csv(credentials, year, month, out_path):

    # the netatmo connect developer credentials, retrieved from a .env file
    load_dotenv()
    credentials = credentials

    # configure the authentication
    authentication = patatmo.api.authentication.Authentication(
        credentials = credentials,
        tmpfile = "temp_auth.json"
    )

    # create a api client
    client = patatmo.api.client.NetatmoClient(authentication)


    #Retrieve the devices of Milan

    # lat/lon outline of Milan/Italy, devided into 7 squares because of API requests limits

    # Square 1.1
    milan_metropole = {
        '1-1' : 
            {"lat_ne" : 45.65191141,
            "lat_sw" : 45.451900,
            "lon_ne" : 8.9900000,
            "lon_sw" : 8.7000000,
            },
        '1-2': 
            {
            "lat_ne" : 45.451900,
            "lat_sw" : 45.251900,
            "lon_ne" : 8.9900000,
            "lon_sw" : 8.7000000,
            },
        '2-1':
            {
            "lat_ne" : 45.65191141,
            "lat_sw" : 45.451900,
            "lon_ne" : 9.2800000,
            "lon_sw" : 8.9900000,
            },
        '2-2':
            {
            "lat_ne" : 45.451900,
            "lat_sw" : 45.251900,
            "lon_ne" : 9.2800000,
            "lon_sw" : 8.9900000,
            },
        '3-1': 
            {
            "lat_ne" : 45.65191141,
            "lat_sw" : 45.451900,
            "lon_ne" : 9.5700000,
            "lon_sw" : 9.2800000,
            }, 
        '3-2': {
            "lat_ne" : 45.451900,
            "lat_sw" : 45.251900,
            "lon_ne" : 9.5700000,
            "lon_sw" : 9.2800000,
            },
        '4':{
            "lat_ne" : 45.20457975,
            "lat_sw" : 45.160000,
            "lon_ne" : 9.5350000,
            "lon_sw" : 9.43654192,
            }
    }

    square_list = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4"]


    # YEAR TO EXTRACT 
    year = year


    nb_request=0

    #For all the year, make the range of months from 1 to 12; Otherwise modify the range
    for m in range(month, month+1):

        print(year)

        for square in square_list:
            # API request for stations and current measures
            milan = client.Getpublicdata(region = milan_metropole[square], required_data='temperature', filter= True)
            nb_request+=1

            #Put the stations info in a list of dictionnaries
            devices_list = []


            for device in milan.response['body']:
                device_data = {
                    'device_id': device['_id'], 
                    'module_id': device['modules'][0],
                    'location': device['place']['location'],
                    'timezone': device['place']['timezone'], 
                    'country': device['place']['country'], 
                    'altitude': device['place'].get('altitude', -999),
                    'city': device['place'].get('city', ''), 
                    'street': device['place'].get('street', '')
                    }
                devices_list.append(device_data)

            #Now, retrieve the data of the selected date for each device

            #Start and end time for the measures
            if m < 9:
                date_start_str = str(year)+'-0'+str(m)+'-01 00:00:00'
                date_end_str = str(year)+'-0'+str(m+1)+'-01 00:00:00'
            elif m == 9:
                date_start_str = str(year)+'-0'+str(m)+'-01 00:00:00'
                date_end_str = str(year)+'-'+str(m+1)+'-01 00:00:00'
            elif m != 12:
                date_start_str = str(year)+'-'+str(m)+'-01 00:00:00'
                date_end_str = str(year)+'-'+str(m+1)+'-01 00:00:00'
            else:
                date_start_str = str(year)+'-'+str(m)+'-01 00:00:00'
                date_end_str = str(year+1)+'-01-01 00:00:00'

            start_datetime = datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S")
            end_datetime = datetime.strptime(date_end_str, "%Y-%m-%d %H:%M:%S")

            start_timestamp = start_datetime.replace(tzinfo=timezone.utc).timestamp()
            end_timestamp = end_datetime.replace(tzinfo=timezone.utc).timestamp()


            print("The number of devices:")
            print(len(devices_list))
            frames=[]

            if len(devices_list) >0 :

                for device in devices_list:
                    if (device['location'][1]<milan_metropole[square]['lat_ne'] and 
                        device['location'][1]>milan_metropole[square]['lat_sw'] and 
                        device['location'][0]<milan_metropole[square]['lon_ne'] and 
                        device['location'][0]>milan_metropole[square]['lon_sw']):

                        time.sleep(2)
                        nb_request+=1
                        print(nb_request)

                        if nb_request > 470:
                            #To know the the current time 
                            currDate = datetime.now()
                            print(currDate)

                            print("Let's wait 45 min")
                            time.sleep(2700)
                            nb_request=0

                        # API request to retrieve data from the outdoor module
                        try: 
                            outdoor = client.Getmeasure(
                                device_id = device['device_id'], 
                                module_id = device['module_id'],
                                scale = "1hour",
                                type = ["Temperature", 'min_temp', 'max_temp'],
                                date_begin = start_timestamp,
                                date_end = end_timestamp,
                                )

                            outdoor_df = outdoor.dataframe()

                            if not outdoor_df.empty:
                                outdoor_df = outdoor_df.assign(
                                    device_id=device['device_id'],
                                    module_id=device['module_id'],
                                    lat=device['location'][1],
                                    long=device['location'][0],
                                    timezone=device['timezone'],
                                    country=device['country'],
                                    altitude=device['altitude'],
                                    city=device['city'],
                                    street=device['street']
                                    )
                                frames.append(outdoor_df)

                        except ApiResponseError as e:
                            print('ERROR WITH API RESPONSE')
                            print(e)
                            print(vars(e))
                            time.sleep(240)
                            pass

                df_result = pd.concat(frames)
                print(df_result)

                # Put the result in a csv file
                milan_csv_data = df_result.to_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s%s.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                                        date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                                        date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                                        end_datetime.minute,square), index = True)

            print('The number of requests made:')
            print(nb_request)

            #To know the the current time 
            currDate = datetime.now()
            print(currDate)

            print("Just wait 5 min")
            time.sleep(300)


# ----------------------------------------------------------------------

def concat_csv_files(year, month, out_path):

    if month > 9:
        date_start_str = str(year) + '-' + str(month) + '-01 00:00:00'
        if month == 12:
            date_end_str = str(year+1) + '-01' + '-01 00:00:00'
        else: date_end_str = str(year) + '-' + str(month+1) + '-01 00:00:00'
    elif month <= 9:
        date_start_str = str(year) + '-0' + str(month) + '-01 00:00:00'
        if month == 12:
            date_end_str = str(year+1) + '-01' + '-01 00:00:00'
        else: date_end_str = str(year) + '-0' + str(month+1) + '-01 00:00:00'


    start_datetime = datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(date_end_str, "%Y-%m-%d %H:%M:%S")
    start_timestamp = start_datetime.replace(tzinfo=timezone.utc).timestamp()
    end_timestamp = end_datetime.replace(tzinfo=timezone.utc).timestamp()


    # If you used different times or names, you can replace each of the following lines by 
    # df_x = pd.read_csv('name_of_your_file.csv') and modify the line 53 with your df_x !

    df1_1 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s1-1.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df1_2 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s1-2.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df2_1 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s2-1.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df2_2 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s2-2.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df3_1 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s3-1.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df3_2 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s3-2.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df4 = pd.read_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_s4.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute))

    df_concat = pd.concat([df1_1, df1_2, df2_1, df2_2, df3_1, df3_2, df4])

    print(df_concat)

    milan_csv_data = df_concat.to_csv(out_path + '/temp_Net_milan_%s-%s-%s_%sh%s-%s-%s-%s_%sh%s_concat.csv' % (date_start_str[8:10], date_start_str[5:7], 
                                                            date_start_str[:4], start_datetime.hour,start_datetime.minute,
                                                            date_end_str[8:10], date_end_str[5:7], date_end_str[:4], end_datetime.hour,
                                                            end_datetime.minute), index = True)

    
    
# ----------------------------------------------------------------------

def filter_netatmo_stations(year, month, aoi, out_path):
    
    # create GeoDataFrame with the boundary of the area of interest (from GeoPackage file)
    gdf_geopackage = gpd.read_file('aoi.gpkg', crs='EPSG:4326')
    
    # create a DataFrame with the Netatmo observations
    data = out_path + '/temp_Net_milan_%s-%s.csv' % (year, month)
    df_csv = pd.read_csv(data)
    
    # turn the DataFrame to a GeoDataFrame with associated coordinates
    gdf_csv = gpd.GeoDataFrame(df_csv, geometry=gpd.points_from_xy(df_csv.long, df_csv.lat), crs='EPSG:4326')
    
    # filter Netatmo observations within the area of interest with a spatial join
    filtered_data = gpd.sjoin(gdf_csv, gdf_geopackage, predicate='within')
    
    # select only the original columns
    filtered_data = filtered_data[list(gdf_csv.columns)]
    
    # save the filtered file to a csv
    out_file = out_path + '/temp_Net_milan_%s-%s_clip.csv' % (year, month)
    filtered_data.to_csv(out_file, index = False)
    
# ----------------------------------------------------------------------

def extract_netatmo_stations(year, month, out_path, gpkg_path):
    
    # read the csv file corresponding to the specified year/month as a pandas dataframe
    df = pd.read_csv(out_path + '/temp_Net_milan_%s-%s_clip.csv' % (year, month))
    
    # create the geometry column starting from the long and lat coordinates
    df['geometry'] = df.apply(lambda row: Point(row['long'], row['lat']), axis = 1)
    
    # convert it to a geodataframe
    gdf = gpd.GeoDataFrame(df, geometry = 'geometry', crs = 'EPSG:4326')
    
    # extract the unique station identifiers
    unique_module_ids = gdf['module_id'].unique()
    
    # extrat the corresponding rows (without diplicates)
    filtered_gdf = gdf[gdf['module_id'].isin(unique_module_ids)].drop_duplicates(subset = 'module_id')
    
    # extract the relevant columns
    filtered_gdf = filtered_gdf[['device_id', 'module_id', 'lat', 'long', 'altitude', 'city', 'street', 'geometry']]
    
    # save it to a geopackage
    filtered_gdf.to_file(gpkg_path + '/sensors_%s-%s.gpkg' % (year, month), driver = 'GPKG')
