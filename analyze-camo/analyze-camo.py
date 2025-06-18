from os import listdir
import json
from matplotlib.colors import hex2color
from matplotlib.pylab import rand
import numpy as np
import ctypes
import skimage as ski
from PIL import Image, ImageFilter
import numpy as np

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

import matplotlib.pyplot as plt

#this is all feeling very whack to me. There has to be a better way for us to extract colors from crappy jpgs w/ the camo print. Compression leads too an excessive amount of noise & color blending. Maybe this is a machine learning job

def rgb_to_hex(color : np.array):
    #print(f"rgb_to_hex: input recieved type: {type(color)}" )
    red, green, blue = color
    return '#%02x%02x%02x' % (int(red), int(green), int(blue))

def plot_colors(hex_array):
    # Create a horizontal bar of colors
    n_colors = len(hex_array)
    fig, ax = plt.subplots(figsize=(n_colors, 1))
    ax.imshow(
        [list(map(hex2color, hex_array.flatten()))],
        aspect='auto',
        extent=[0, n_colors, 0, 1]
    )
    ax.set_xticks([])
    ax.set_yticks([])
    plt.show()

def analyze_camo() -> None:
    #json = json_load("./analyze-camo/camo-data.json")
    camoset_dir = "./analyze-camo/camoset"
    for image in listdir(camoset_dir):
        #print ("test")
        if (image.endswith((".png", ".jpg",".jpeg"))):
            #print('reeee')
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
                cluster_centers = quantize_colors(flat_array)
                hex_array = np.empty((cluster_centers.shape[0], 1), dtype=object)
                print(f"Cluster centers range: min={cluster_centers.min()}, max={cluster_centers.max()}")
                for i, element in enumerate(cluster_centers):
                    hex_array[i] = rgb_to_hex((
                        int(element[0]), 
                        int(element[1]),
                        int(element[2])
                        ))
                print(cluster_centers)
                print(hex_array)
                #plot_colors(hex_array)
                #refine_call(flat_array)
                

def quantize_colors(array):
    #for number of colors peep silhouette analysis https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html#sphx-glr-auto-examples-cluster-plot-kmeans-silhouette-analysis-py
    n = n_colors_best_fit(array)
    kmeans = KMeans(n_clusters=n, random_state=24)
    kmeans_labels = kmeans.fit_predict(array)   #kmeans_label currently redundant
    trimmed_array = trim(array, kmeans_labels)
    kmeans.fit_predict(trimmed_array)                   #run again now that we have trimmed poorly fit colors out
    return kmeans.cluster_centers_

def trim(array, labels):
    sil_vals_array = np.array(silhouette_samples(array, labels))
    del_indicies = np.where(sil_vals_array < .3 )
    array = np.delete(array, del_indicies, axis=0)
    with open('flat_array.txt', "w+") as txt:
        for val in sil_vals_array:
            txt.write(f"{val}\n")
    return array

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