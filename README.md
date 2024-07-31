# Cleaning, plotting and analysis of Netatmo air temperature data

This Repository contains Jupyter Notebooks and Python functions implementing a multi-step cleaning workflow for Netatmo crowdsourced air temperature data.

[**Netatmo**](https://www.netatmo.com/) is a commercial manufacturer and data aggregator of citizen weather stations, distributing low-cost weather stations for citizens around the world with the aim of monitoring outdoor and indoor weather conditions (e.g., temperature and humidity). Netatmo stations take advantage of Wi-Fi connection for data transfer and automatic upload on a dedicated server, and owners have access to real-time data visualization via application software. Observations are publicly shared through a dedicated Application Programming Interface (API), which enables free data download within the limits expressed by the provider.

Netatmo data is retrieved through the package [`patatmo`](https://nobodyinperson.gitlab.io/python3-patatmo/), using two dedicated methods. The former, `Getpublicdata`, is used to get instantaneous measurements from all stations within a specific geographic area along with the corresponding metadata (e.g., station identifier, latitude, and longitude). The latter, `Getmeasure`, allows data retrieval for a specific station in a given time range and is thus used to extract temperature time histories recorded by each station.

Notebooks:
* [`1 - Download_data.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/1%20-%20Download_data.ipynb): download of Netatmo data in a specified area of interest.
* [`2a - Data_cleaning.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/2a%20-%20Data_cleaning.ipynb): multi-step cleaning procedure for ARPA Lombardia and Netatmo data as described in [1]. A further step is added, consisting of the removal of unreliable stations, i.e. stations with more than 50% of measurements removed after data cleaning.
* [`2b - Data_cleaning_pt2.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/2b%20-%20Data_cleaning_pt2.ipynb), [`2c - Data_cleaning_pt3.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/2c%20-%20Data_cleaning_pt3.ipynb), and [`2d - Data cleaning_pt4.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/2d%20-%20Data%20cleaning_pt4.ipynb): visualisation of the reliability index and of the correlation coefficient.
* [`3 - Data_visualization.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/3%20-%20Data_visualization.ipynb): interactive visualisation of Netatmo data, before and after each cleaning step; the user can visualise histograms, maps, and time series with the statistics (minimum, maximum, mean, standard deviation, and median) of time series with daily, monthly, and yearly aggregation.
* [`4 - Spatial_indices.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/4%20-%20Spatial_indices.ipynb): computation of two indices based on time series quantiles; the indices are the 10th and 90th percentile of the time series, divided by the 10th and 90th percentile of the average time series (obtained as the hourly average of all the stations). Preliminarily, the time series completeness is computed as the percentage of Netatmo measurements kept after data cleaning and the number of measurements that would be there in case of complete time series.
* [`5 - LCZ_correlation.ipynb`](https://github.com/albertovavassori/Netatmo_data_analysis/blob/main/5%20-%20LCZ_correlation.ipynb): correlation analysis between the Netatmo air temperature data and local climate zones (LCZs).

-----------------------------------------------------------------------

[1] Puche, M.; Vavassori, A.; Brovelli, M.A. **Insights into the Effect of Urban Morphology and Land Cover on Land Surface and Air Temperatures in the Metropolitan City of Milan (Italy) Using Satellite Imagery and In Situ Measurements**. *Remote Sens.* 2023, 15, 733. https://doi.org/10.3390/rs15030733


-----------------------------------------------------------------------

<ins><b>Authors</b></ins>: <b>*Alberto Vavassori*</b> (alberto.vavassori@polimi.it), <b>*Ahmed Omer Ahmed Mukhtar*</b> (ahmed.mukhtar@mail.polimi.it), <b>*Ahmed Mohamed Eltahir Yassin*</b> (ahmedmohamed1@mail.polimi.it), <b>*Mathilde Puche*</b> (mathildedanielle.puche@mail.polimi.it), <b>*Andrea Folini*</b> (andrea.folini@mail.polimi.it) - Politecnico di Milano.
