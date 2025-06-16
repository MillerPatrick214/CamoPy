import io
import re
from typing import Type
from xml.etree.ElementTree import PI
from matplotlib.colors import hex2color
from core import Sentinel, Request
import datetime
import pandas as pd
import numpy as np 
import rioxarray
from rioxarray import merge
import matplotlib.pyplot as plt
import squarify
from PIL import Image
from stratify import Stratify


def toText(array):
    with open("color_strata_test.txt", "w+") as txt:
        for object in array:
            txt.writelines(f"Tuple: {object[0]} ----- Count: {object[1]}\n")

def rgb_to_hex(color : tuple):
    #print(f"rgb_to_hex: input recieved type: {type(color)}" )
    red, green, blue = color
    return '#%02x%02x%02x' % (int(red), int(green), int(blue))

def xarray_to_buffer(array):
    data = array.values
    data = np.stack(data, axis=-1)
    data = data.astype(np.uint8)

    buffer = io.BytesIO()
    np.save(buffer, data)
    buffer.seek(0)

    return buffer

def xarray_to_PIL(tif):
    data = tif.values #has shape of (3, y, x)    
    combined = np.stack(data, axis=-1) #shape (x, y, 3)
    combined = combined.astype(np.uint8)
    image = Image.fromarray(combined, mode="RGB")
    return image

def filter_colors_numpy(array):
    pass

        
def camo_request(latitude, longitude, area, month):     
    curr_year = datetime.datetime.now().year
    prev_year = str(curr_year - 1)
    month = str(month) if len(str(month)) == 2 else "0" + str(month)
    startdate = prev_year + "-" + month
    enddate = ""                                        #must be changed in the future to accomodate seasons, etc. keeping it simple w/ 1 month rn tho

    ticket = Request(startdate, latitude, longitude, enddate, box_size=area)  
    items = Sentinel.PullMatches(ticket)

    data_list = []
    cloud_counter = 0
    #print("Checkpoint 1: Initialized data_list and cloud_counter")

    for item in items:                      
        #print("Checkpoint 2: Entered loop for processing items")

        cloud_coverage = item.properties["eo:cloud_cover"]
        #print(f"Checkpoint 3: Retrieved cloud_coverage: {cloud_coverage}")

        if cloud_coverage > 40:
            cloud_counter += 1
            #print(f"Too many clouds... Discarded: {cloud_counter} matches")
            continue
        
        #print("Checkpoint 4: Cloud coverage acceptable, processing item")

        assets = item.assets  
        #print("Checkpoint 5: Retrieved assets")

        tci_href = assets["visual"].href
        #print(f"Checkpoint 6: Retrieved tci_href: {tci_href}")

        tc = rioxarray.open_rasterio(tci_href, masked=True).rio.clip(ticket.geometries, from_disk=True)
        #print("Checkpoint 7: Clipped tc raster")

        to_omit = [6, 7, 8, 9]
        #print(f"Checkpoint 8: Defined values to omit: {to_omit}")

        scl_href = assets["scl"].href
        #print(f"Checkpoint 9: Retrieved scl_href: {scl_href}")

        scl = rioxarray.open_rasterio(scl_href, masked=True).rio.clip(ticket.geometries, from_disk=True)
        #print("Checkpoint 10: Clipped scl raster")

        scl = scl.rio.reproject_match(tc)
        #print("Checkpoint 11: Reprojected scl to match tc dimensions")
        
        mask = np.isin(scl.values, to_omit)                                    
        #print("Checkpoint 12: Created mask for to_omit values")
        
        nd_indicies = np.where(mask == True)  # indices we want to set
        #print(f"Checkpoint 13: Found nd_indicies: {nd_indicies}")
        
        tc.values[:, nd_indicies[1], nd_indicies[2]] = 0  # Set values to 0 where indices match
        #print("Checkpoint 14: Updated tc.values to set nd_indices to 0")

        data_list.append(tc)
        #print(f"Checkpoint 15: Appended tc to data_list. Current data_list length: {len(data_list)}")

    
    merged = merge.merge_arrays(data_list, nodata = 0 )

    merged.encoding = { k : v for k, v in merged.encoding.items() if k != "_FillValue"} #this fixes the "ValueError: failed to prevent overwriting existing key _FillValue in attrs" error.

    #merged.rio.to_raster("mosaic_test.tif")
    

    color_array = np.stack(merged.values, axis=2, dtype=np.float64)         #sample across arrays and gather values as tuples (r,g,b)               This float64 is cucking the memory
    #color_array.astype(np.int8)                                         #min-max values are 0-255. Can fit these within an 8 bit integer        float64 is cucking the memory but this cast to int8 is cucking the entire program. 
    
    color_array = color_array[:, :, :3].reshape((-1, 3))

    color_array = [(R, G, B) for R, G, B in color_array if (R, G, B) != (0, 0, 0)]         #list comprehension, turn that shit into a list of tuples. Took me way too long to figure out this was the best solutions 
    
    print(F"FIRST ELEMENT OF COLOR ARRAY: {color_array[0]}")  
    
    #Pandas work for filtering to IQR colors ------------------------------------------------------------------------------------------------------------
    print(f"color array {len(color_array)}")    #Patrick from future: but why bring in pandas in the first place? I could easily do this in numpy and avoid additional overhead and converting everything into pandas only to convert it back.
    val_count = pd.Series(color_array, name="colors").value_counts(dropna=True)                   
    color_df = val_count.to_frame()
    color_df = color_df.reset_index()
    color_df.columns = ["colors","counts"]
    print(f"pandas df prior to trim {color_df.size}")

    #print("Original color_df:")
    #print(color_df.head().to_string())              

    color_df["mean_color"] = color_df["colors"].apply(lambda x: np.mean(x))       #lambda function to chune this shit and get a mean
    color_df = color_df[(color_df["mean_color"] < 245.0) & (color_df["mean_color"] > 25.0 )] #low and high intensity color pass    

    Q1 = color_df["mean_color"].quantile(0.25)
    Q3 = color_df["mean_color"].quantile(0.75)

    IQR = Q3 - Q1

    outliers = color_df[(color_df["mean_color"] < Q1 - 1.5 * IQR) | (color_df["mean_color"] > Q3 + 1.5 * IQR)] #def
        
    color_df = color_df[~color_df["colors"].isin(outliers["colors"])]

    rgb_df = color_df.drop(["mean_color"], axis=1)


    print(f"pandas df after trim: {rgb_df.size}")

    rgb_df = rgb_df.to_numpy()
    
    
    #----------------------------------------------




    print(f"size of rgb_df = {rgb_df.size}")
    
    refined_colors = Stratify.stratify(rgb_df) #FIXME FIXME FIXME!!! Core issue here is that the colors must be sorted before being processed in stratify. I will attempt to tackle the problem in Stratify 
    #toText(refined_colors) #does this need to be in here? I don't think so. Try without
    refined_colors[:, 0] = [rgb_to_hex(color) for color in refined_colors[:, 0]]
    
  
    #hex_count_dict = dict(zip(color_df[:, 1], color_df[:, 0])) #counts, colors
    
    #print("ree" + hex_count_dict)

    sort_indicies = np.argsort(refined_colors[:, 1].astype(int))[::-1]
    refined_colors = refined_colors[sort_indicies]

    plt.rc("font", size=12)
    ax = squarify.plot(sizes=refined_colors[:, 1], color=refined_colors[:, 0], alpha=1)
    ax.set_axis_off()

    #convert figure into buffer that we can serve
    fig_buffer = io.BytesIO()
    plt.savefig(fig_buffer, format="PNG", bbox_inches="tight", pad_inches=0)
    fig_buffer.seek(0)

    return xarray_to_PIL(merged), Image.open(fig_buffer)

if __name__ == "__main__":
    merged_image, fig_image = camo_request(32.715736, -117.161087, 5000, 5)


 