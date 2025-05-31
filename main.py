from matplotlib import axis
from shapely.geometry import box
import utm
import pandas as pd
import geopandas
from pystac_client import Client
import numpy as np 
import rioxarray
from rioxarray import merge
import matplotlib.pyplot as plt
import squarify


def rgb_to_hex(color : tuple):

    red, green, blue = color
    return '#%02x%02x%02x' % (int(red), int(green), int(blue))
        
class Request: 
    def __init__(self, start_date : str, latitude : float , longitude : float, end_date : str ='', box_size : int = 5000) -> None: #side_size represents 1 side of the square. default is 1000m for a 1km squared area
        self.latitude = latitude
        self.longitude = longitude
        self.start_date : str = start_date     #YYYY-mm or YYYY-mm-dd
        self.end_date : str = end_date       #YYYY-mm documentation states we can also use a simple string. https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.CollectionSearch also talks about splitting the dates as a range there 
        self.box_size = box_size        # must be in meters
        self.date_request = start_date + '/' + end_date if (end_date) else start_date
        self.bbox = self.pystac_bbox()
        self.geodf = self.gen_geodf(self.bbox)
        self.geometries = self.gen_geometries()
        
    def pystac_bbox(self) -> list:
        eassting, northing, zone_number, zone_letter = utm.from_latlon(self.latitude, self.longitude)
        #print(f"\nUTM DATA FROM POINT:\n  eassting:{eassting}\n  northing:{northing}\n  zone_number:{zone_number}\n  zone_letter:{zone_letter}\n\n") #DEBUG--FIXME
        box_points = []
        for i in [-1, 1]:
            coords = utm.to_latlon((eassting + (i*self.box_size/2)),(northing +(i*self.box_size/2)), zone_number, zone_letter)
            box_points.append(coords[1])
            box_points.append(coords[0])

            #print(f"\nNEW MIN/MAX COORDS FROM MODIFIED UTMs:\n  latitude:{coords[0]}\n  longitude:{coords[1]}\n\n") #DEBUG--FIXME

        return box_points
    
    def gen_geodf(self, bbox) -> dict:  #used specifically for clipping w/ rasterio. we may not need this in the long haul. Now using the more memory efficient rio.clip function (crazy big performance improvement)

        geodf = geopandas.GeoDataFrame(
            geometry = [
                box(bbox[0], bbox[1], bbox[2], bbox[3])
            ],
            crs="EPSG:4326"
        )
        return geodf
    
    def gen_geometries(self):     #useful for more memory efficient raster clipping operation
        eassting, northing, zone_number, zone_letter = utm.from_latlon(self.latitude, self.longitude)
        
        geometries = [
            {
            'type': 'Polygon',
            'coordinates': [[]]
            }
        ]


        j_order = [1, -1]
        for i in [1, -1]:
            for j in j_order:
                coords = [(eassting + (i*self.box_size/2)),(northing +(j*self.box_size/2))]
                geometries[0].get("coordinates")[0].append(coords)
            j_order.reverse()                                       # this avoids us drawing a bowtie looking thing. Order matters here 


        return geometries


class Sentinel:
    collection = "sentinel-2-l2a"
    api_url = "https://earth-search.aws.element84.com/v1"
    @staticmethod
    def PullMatches(request : Request):
        client : Client = Client.open(Sentinel.api_url)
        search = client.search(
            max_items = 2,
            bbox= request.bbox,
            collections = [Sentinel.collection],
            datetime= request.date_request
        )
        if (search.matched()):
            print(f"found {search.matched()} matches") 
        else:
            print(f"found {search.matched()} matches. Aborting script")
            quit()
        
        return search.item_collection()
    
#TESTING
startdate = "2023-06"
enddate = "2023-08"
latitude =  36.45172418066291
longitude = -118.17150474920052
#TESTING

if __name__ == "__main__": 
    request = Request(startdate, latitude, longitude, enddate)  
    items = Sentinel.PullMatches(request)

    """"# just looking thru what properties we can grab
    # print(f" Geometry: {items[0].geometry}")
    # print("\n\n")
    # print(f"properties {items[0].properties}")
    # print("\n\n")
    # print(f"assets {items[0].assets}")
    # items.save_object("mccain_valley_sentinel-2.json") save meta data in json                  #save metadata to json

    import pystac    use in external mopdule to import
    items_loaded = pystac.ItemCollection.from_file("mccain_valley_sentinel-2.json")            use in external mopdule to import
   

    for key, asset in items[-1].assets.items(): #useful for seeing what bands we have available
    print(f"{key} : {asset.title}, \n")
    """

    data_list = []
    mosiac : np.ndarray
    
    for item in items:                      
        cloud_coverage = item.properties["eo:cloud_cover"]
        if ( cloud_coverage > 40):
            continue
        assets = item.assets  
        tci_href = assets["visual"].href
        tc = rioxarray.open_rasterio(tci_href, masked=True).rio.clip(request.geometries, from_disk=True)  #more memory efficient to do the clipping here.
        #print (tc.values.shape)

        #FIXME DEBUG DEBUG DEBUG========================================================================================================
       
        to_omit = [6, 7, 8, 9]
        scl_href = assets["scl"].href
        scl = rioxarray.open_rasterio(scl_href, masked=True ).rio.clip(request.geometries, from_disk=True)
        scl = scl.rio.reproject_match(tc)    #reprojecting so that our project's values match the same dim as tc
                
        #print (scl.values.shape)
        mask = np.isin(scl.values, to_omit)
        # print(mask)
    
        """with np.nditer(scl.values, op_flags=['readwrite']) as it:            #this overwrites all cloud data to ND. If we save the index for the equivalent visual layer, can't we just make those pix nd too? Or an array of indicies for our color picker to skip?
            for x in it:
                if x in to_omit:
                    x[...] = 0
                    it.index
        """
        
        nd_indicies = np.where(mask == True)        #indicies we went to set 
        
        tc.values[:, nd_indicies[1], nd_indicies[2]] = 0                    # slice across all bands, wherever our nd_indicies appear set =0
        #tc.rio.set_nodata(0, inplace=True)
        data_list.append(tc)
    
    merged = merge.merge_arrays(data_list, nodata = 0 )   

    merged.encoding = { k : v for k, v in merged.encoding.items() if k != "_FillValue"} #this fixes the "ValueError: failed to prevent overwriting existing key _FillValue in attrs" error.

    merged.rio.to_raster("mosaic_test.tif")

    color_array = np.stack(merged.values, axis=2, dtype=np.float64)         #sample across arrays and gather values as tuples (r,g,b)               This float64 is cucking the memory
    #color_array.astype(np.int8)                                         #min-max values are 0-255. Can fit these within an 8 bit integer        float64 is cucking the memory but this cast to int8 is cucking the entire program. 
    
    color_array = color_array[:, :, :3].reshape((-1, 3))

    color_array = [(R, G, B) for R, G, B in color_array if (R, G, B) != (0, 0, 0)]         #list comprehension, turn that shit into a list of tuples. Took me way too long to figure out this was the best solutions 
    
    print(F"FIRST ELEMENT OF COLOR ARRAY: {color_array[0]}")  
    

    #Pandas work for filtering to IQR colors ---------------------------
    val_count = pd.Series(color_array, name="colors").value_counts(dropna=True)                   
    color_df = val_count.to_frame()
    color_df = color_df.reset_index()
    color_df.columns = ["colors","counts"]

    print("Original color_df:")
    print(color_df.head().to_string())              

    color_df["mean_color"] = color_df["colors"].apply(lambda x: np.mean(x))       #lambda function to chune this shit and get a mean
    color_df = color_df[(color_df["mean_color"] < 230.0) & (color_df["mean_color"] > 25.0 )] #low and high intensity color pass    

    Q1 = color_df["mean_color"].quantile(0.25)
    Q3 = color_df["mean_color"].quantile(0.75)

    IQR = Q3 - Q1

    outliers = color_df[(color_df["mean_color"] < Q1 - 1.5 * IQR) | (color_df["mean_color"] > Q3 + 1.5 * IQR)] #
    
    #outliers = color_df[color_df["counts"] > 100]                           100 is arbitrary here. should probably be a percentage of total pixels? 
    
    color_df = color_df[~color_df["colors"].isin(outliers["colors"])]

    color_df["colors"] = color_df["colors"].apply(lambda color : rgb_to_hex(color))
    print(f"print(color_df.head()): {color_df.head()}")
        
    RGB_count_dict = dict(zip(color_df.counts, color_df.colors)) 
    
    print(RGB_count_dict)

    plt.rc("font", size=12)
    squarify.plot(sizes=RGB_count_dict.keys(), label=RGB_count_dict.values(), color=RGB_count_dict.values(), alpha=1)
    plt.axis('on')
    plt.show() 


    


