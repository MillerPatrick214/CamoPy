import utm
import geopandas
from shapely.geometry import box
from pystac_client import Client
import numpy
import rioxarray
from rioxarray import merge
from rasterio import CRS

#will need args for a date range (2 dates), box size, lat and longitude


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
    
    def gen_geodf(self, bbox) -> geopandas.GeoDataFrame:  #used specifically for clipping w/ rasterio. we may not need this in the long haul. Now using the more memory efficient rio.clip function (crazy big performance improvement)

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
            max_items = 7,
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
    

