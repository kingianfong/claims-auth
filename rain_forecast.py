import ast
import pandas as pd
import re
import urllib.request as ur

rf_url = "https://api.data.gov.sg/v1/environment/rainfall"
rf_source = ur.urlopen(rf_url).read().decode('utf-8')
rf_source = ast.literal_eval(rf_source)

rf_time = rf_source["items"][0]["timestamp"].split("T")
rf_time = f"{rf_time[0]}_{rf_time[1].split('+')[0]}"
rf_time = re.sub(r'\W+', '', rf_time)

stations = pd.DataFrame(rf_source["metadata"]["stations"]).set_index("device_id", drop = True)
stations["Latitude"] = stations["location"].apply(lambda i: i["latitude"])
stations["Longitude"] = stations["location"].apply(lambda i: i["longitude"])

rainfall = ( pd.DataFrame(rf_source["items"][0]["readings"])
             .join(stations,on = "station_id")
             .drop(columns=["station_id", "id", "location"])
             .rename(columns={"value": "5m Total (mm)", "name": "area"})
             .set_index("area", drop = True) )

def raining(rainfall):
    if rainfall > 0.2:  #treshold of 5mm
        return 1
    else:
        return 0
    
rainfall["label"] = rainfall["5m Total (mm)"].apply(lambda i: raining(i))

fc_url = "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast"
fc_source = ur.urlopen(fc_url).read().decode('utf-8')
fc_source = ast.literal_eval(fc_source)

fc_time = fc_source["items"][0]["timestamp"].split("T")
fc_time = f"{fc_time[0]}_{fc_time[1].split('+')[0]}"
fc_time = re.sub(r'\W+', '', fc_time)

locations = pd.DataFrame(fc_source["area_metadata"]).set_index("name", drop = True)
locations["Latitude"] = locations["label_location"].apply(lambda i: i["latitude"])
locations["Longitude"] = locations["label_location"].apply(lambda i: i["longitude"])

forecast = ( pd.DataFrame(fc_source["items"][0]["forecasts"])
             .set_index("area", drop = True)
             .join(locations)
             .drop(columns = ["label_location"]) )

def severity(forecast):
    severity = {None: 0,
                "Partly Cloudy (Day)": 0,
                "Cloudy": 0,
                "Showers": 1,
                "Light Rain": 1,
                "Moderate Rain": 1,
                "Heavy Rain": 1,
                "Thundery Showers": 1,
                "Heavy Thundery Showers with Gusty Winds": 1}
    try:
        return severity[forecast]
    except:
        return 0
    
forecast["label"] = forecast["forecast"].apply(lambda i: severity(i))

def plot_prediction():
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    plt.ylabel("Latitude")
    plt.xlabel("Longitude")

    img = mpimg.imread('sg_map.png')
    
    imgx, imgy = 2430, 1380
    width_over_height = imgx/imgy
    
    ymax, ymin = 1.485, 1.189
    height = ymax - ymin
    width = height * width_over_height
    xmin = 103.575
    xmax = xmin + width

    plt.imshow(img, extent = (xmin, xmax, ymin, ymax))

    axes = plt.gca()
    axes.set_xlim([xmin, xmax])
    axes.set_ylim([ymin, ymax])
    
    if len(rainfall[ rainfall["label"] == 0]) != 0:
        plt.scatter(rainfall[rainfall["label"] == 0]["Longitude"],
                    rainfall[rainfall["label"] == 0]["Latitude"],
                    c = '0.4',
                    label = "not raining",
                    marker = 'x')
    
    if len(rainfall[ rainfall["label"] == 1]) != 0:
        plt.scatter(rainfall[rainfall["label"] == 1]["Longitude"],
                    rainfall[rainfall["label"] == 1]["Latitude"],
                    c = 'r',
                    label = "raining")
        
    if len(forecast[ forecast["label"] == 0]) != 0:    
        plt.scatter(forecast[forecast["label"] == 0]["Longitude"],
                    forecast[forecast["label"] == 0]["Latitude"],
                    c = (0.1, 0.4, 0.4),
                    label = "no rain forecasted",
                    marker = '+')
    
    if len(forecast[ forecast["label"] == 1]) != 0:
        plt.scatter(forecast[forecast["label"] == 1]["Longitude"],
                    forecast[forecast["label"] == 1]["Latitude"],
                    c = 'm',
                    label = "rain forecasted")
    plt.scatter(user_longitude, user_latitude, c = colour, s = 150, label = message, marker = "*")
    plt.legend(loc = "lower right")
    plt.show()
    return

user_longitude, user_latitude = 103.85, 1.31  # default values: 103.85, 1.31

from sklearn.neighbors import KNeighborsClassifier
rf_clf = KNeighborsClassifier(n_neighbors = 3, weights = 'distance', metric = "euclidean")
fc_clf = KNeighborsClassifier(n_neighbors = 3, weights = 'distance', metric = "euclidean")
rf_clf.fit(rainfall[["Longitude", "Latitude"]], rainfall["label"].values)
fc_clf.fit(forecast[["Longitude", "Latitude"]], forecast["label"].values)

[rf] = rf_clf.predict([[user_longitude, user_latitude]])
[fc] = fc_clf.predict([[user_longitude, user_latitude]])

if rf == 1 and fc == 1:
    colour, message = 'r', f'raining, forecasted to continue'
elif fc == 1:
    colour, message = 'm', f'no rain, forecasted to rain'
elif rf == 1:
    colour, message = 'r', f'raining, forecasted to stop'
else:
    colour, message = 'c', f'no rain, no rain forecasted'

print(f"{message} at longitude {user_longitude}, latitude {user_latitude}")
plot_prediction()
