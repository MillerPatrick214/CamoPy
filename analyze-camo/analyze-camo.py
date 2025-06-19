from os import listdir
import json
import numpy as np
from PIL import Image
import numpy as np

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

import matplotlib.pyplot as plt

#this is all feeling very whack to me. There has to be a better way for us to extract colors from crappy jpgs w/ the camo print. Compression leads too an excessive amount of noise & color blending. Maybe this is a machine learning job

def rgb_to_hex(color : np.array):
    #print(f"rgb_to_hex: input recieved type: {type(color)}" )
    red, green, blue = color
    return '#%02x%02x%02x' % (int(red), int(green), int(blue))

def plot_colors(color_dict: dict):

    colors = list(color_dict.keys())
    percentages = np.array(list(color_dict.values()))
    
    # normalize percentages to sum to 1 in case of rounding errors
    percentages = percentages / percentages.sum()
    
    fig, ax = plt.subplots(figsize=(8, 1))
    
    start = 0
    for pct, color in zip(percentages, colors):
        ax.barh(0, width=pct, left=start, color=color, height=1)
        start += pct

    ax.set_xlim(0, 1)
    ax.set_axis_off()
    plt.show()

def analyze_camo() -> None:
    camo_path = "./analyze-camo/camo-data.json"

    with open(camo_path, "r") as jsn:
        try:
            camo_dict : dict = json.load(jsn)
            camoset_dir = "./analyze-camo/camoset"
        except json.JSONDecodeError as e:
                print(f"Warning: {camo_path} not a valid JSON file or empty buddy. Initializing as empty dictionary.")
                camo_dict = {}

        for image in listdir(camoset_dir):
            if not image.endswith((".png", ".jpg",".jpeg")): continue 

            name = image.split('.')
        
            #if name[0] in camo_dict.keys(): continue        #With this uncommented it will not update already existing camos in the DB. 
            entry = {
                name[0] : {         #name[0] str 
                    #color : count
                }

            }
            camo_dict.update(entry)


            with Image.open(f"{camoset_dir}/{image}") as img:
                img = img.resize((150,150))                                 #need to resize this or it takes like at least an hour per image
                #filtered_img = img.filter(ImageFilter.MedianFilter(size=3)) #this works incredibly well at removing noise from JPG images
                #img.show()
                #filtered_img.show()
                img_array = np.array(img, dtype = np.uint8)
                height, width, bands = img_array.shape
                flat_array = img_array.reshape(height * width, bands) #collapse height and width to make 2 d (pixels, bands)
                #flat_array = np.unique(flat_array, axis=0) I think only passing a unique array is biting us in the ass as I'm not letting frequency suggest which way the mean color leans.
                #the other side of this, tho, is that it takes FOREVER to run 
                entry = quantize_color(entry, flat_array)
                normalize_counts(entry)
                print(entry)
                plot_colors(entry[name[0]])
                #refine_call(flat_array)a
                camo_dict.update(entry)
        
            with open(camo_path, "w") as jsn:
                json.dump(camo_dict, jsn, indent=4)
                

def quantize_color(entry : dict, array :np.ndarray) -> dict:
    #for number of colors peep silhouette analysis https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html#sphx-glr-auto-examples-cluster-plot-kmeans-silhouette-analysis-py
    n = n_colors_best_fit(array)
    kmeans = KMeans(n_clusters=n, random_state=24)
    kmeans_labels = kmeans.fit_predict(array)   #kmeans_label currently redundant
    trimmed_array = trim(array, kmeans_labels)
    kmeans.fit_predict(trimmed_array)                   #run again now that we have trimmed poorly fit colors out
    unique_labels, counts = np.unique(kmeans_labels, return_counts=True)
    
    name = list(entry.keys())[0]
    for i, center in enumerate(kmeans.cluster_centers_):
        hex_color = rgb_to_hex((                    
                int(center[0]),    #R
                int(center[1]),    #G
                int(center[2])))   #B
        entry[name][hex_color] = counts[i]

    return entry

def trim(array, labels):
    sil_vals_array = np.array(silhouette_samples(array, labels))
    del_indicies = np.where(sil_vals_array < .3 )
    array = np.delete(array, del_indicies, axis=0)
    with open('flat_array.txt', "w+") as txt:
        for val in sil_vals_array:
            txt.write(f"{val}\n")
    
    return array

def normalize_counts(entry : dict) -> dict:
    name = list(entry.keys())[0]
    hexes = list(entry[name].keys())
    count = 0
    for hex in hexes:
        count += int(entry[name][hex])
    
    for hex in hexes:
        entry[name][hex] = float(entry[name][hex]/count)
    
    return entry

def n_colors_best_fit(array):    #damn this takes a while
    scores = {4:-1.0} #{2 :-1.0, 3:-1.0, 4:-1.0, 5:-1.0, 6:-1.0, 7:-1.0, 8:-1.0, 9:-1.0, 10:-1.0}       #this is a crazy expensive operation -- use histogram to make a rough guess within +-1 of estimate?
    for n_cluster in scores.keys(): #assumes that any given camo will have between 2 to 10 unique colors.
        clusterer = KMeans(n_clusters=n_cluster, random_state=10)
        cluster_labels = clusterer.fit_predict(array)
        silhouette_avg = silhouette_score(array, cluster_labels)
        print(
            "For n_clusters =",
            n_cluster,
            "The average silhouette_score is :",
            silhouette_avg,
        )
        scores[n_cluster] = silhouette_avg

    best_fit = list(scores.keys())[0] 
    for key, val in scores.items():
        if val > scores.get(best_fit):
            best_fit = key

    return best_fit
    #God damn this takes a long time -- would love to be able to speed up.

      
if __name__ == "__main__":
    analyze_camo()