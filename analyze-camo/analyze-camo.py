from os import listdir
import json
from pydoc import text
import tkinter
import numpy as np

import PIL.Image    # confusion between this image class and tkinters. Going to keep the 3 PIL classes we need in this format to avoid confusion
import PIL.ImageTk
import PIL.ImageFilter

import numpy as np

from shapely import length
import skimage as ski

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

from tkinter import *
from tkinter import ttk

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
        
            if name[0] in camo_dict.keys(): continue        #With this uncommented it will not update already existing camos in the DB. 
            entry = {
                name[0] : {         #name[0] str 
                    #color : count
                }
            }
            camo_dict.update(entry)


            with PIL.Image.open(f"{camoset_dir}/{image}") as img:
                if img.mode == "P":
                    img = img.convert("RGB")
                large_img = img.resize((750,750))                                 #need to resize this or it takes like at least an hour per image
                distinct_colors_n = n_colors_gui(large_img)
                img = img.resize((300,300))                                 #need to resize this or it takes like at least an hour per image
                filtered_img = img.filter(PIL.ImageFilter.MedianFilter(size=3))
                img_array = np.array(filtered_img, dtype = np.uint8)
                height, width, bands = img_array.shape

                if (bands != 3):                                                     # I guess the only issue with this is that there may be images where alpha band does matter. I will have to correct this in the future to make it bullet proof
                    try:
                        img_array = np.delete(img_array, -1, axis=2)
                        bands = img_array.shape[2]
                        if (not bands == 3): 
                            error = ValueError(f"Image doesn't contain expected number of bands (Either 3 for RGB or 4 for RGBA)\nBands before attempting correction {bands + 1}\nBands after attemping correction {bands}")
                            raise error 

                    except ValueError as e:
                        print(f"\033[31mException {e}\033[0m")
                        exit()
                    

                #FIXME DEBUG.
                print("array.shape before resize: ", img_array.shape)
                #np.savetxt("array_before.txt", img_array) Can't save non 2d array like this
                #FIXME DEBUG.

                

                flat_array = img_array.reshape(height * width, bands) #collapse height and width to make 2 d (pixels, bands)

                #FIXME DEBUG.
                print("array.shape after resize: ", flat_array.shape)
                np.savetxt("array_after.txt", flat_array)
                #FIXME DEBUG.

                entry = quantize_color(entry, flat_array, distinct_colors_n)
                normalize_counts(entry)
                print(entry)
                plot_colors(entry[name[0]])
                #refine_call(flat_array)a
                camo_dict.update(entry)
        
            with open(camo_path, "w") as jsn:
                json.dump(camo_dict, jsn, indent=4)
                

def quantize_color(entry : dict, array :np.ndarray, distinct_colors_n: int) -> dict:
    #for number of colors peep silhouette analysis https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html#sphx-glr-auto-examples-cluster-plot-kmeans-silhouette-analysis-py
    kmeans = KMeans(n_clusters=distinct_colors_n, random_state=24)
    lab_array = array_rgb_to_lab(array)
    kmeans_labels = kmeans.fit_predict(lab_array)   #kmeans_label currently redundant
    trimmed_array = trim(lab_array, kmeans_labels)
    kmeans.fit_predict(trimmed_array)                   #run again now that we have trimmed poorly fit colors out
    unique_labels, counts = np.unique(kmeans_labels, return_counts=True)
    
    name = list(entry.keys())[0]
    for i, center in enumerate(ski.color.lab2rgb(kmeans.cluster_centers_) * 255):
        hex_color = rgb_to_hex((                    
                int(center[0]),    #R
                int(center[1]),    #G
                int(center[2])))   #B
        entry[name][hex_color] = counts[i]

    return entry

def n_colors_gui(img: PIL.Image.Image):
    root = Tk()
    root.configure(bg="#2b2b2b")
    root.title("Distinct Colors UI")

    style = ttk.Style()
    style.theme_use("default")  # Use default theme to customize easier

    style.configure("Dark.TFrame", background="#2b2b2b")

    style.configure("Dark.TLabel", background="#2b2b2b", foreground="#ffffff")

    style.configure("Dark.TButton", background="#444444", foreground="#ffffff")
    style.map("Dark.TButton",
              background=[('active', '#555555')])

    style.configure("Dark.TCombobox",
                    fieldbackground="#3c3c3c",
                    background="#3c3c3c",
                    foreground="#000000")

    mainframe = ttk.Frame(root, padding="3 3 12 12", style="Dark.TFrame")
    mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    converted_image = PIL.ImageTk.PhotoImage(image=img)
    camo_image = ttk.Label(mainframe, image=converted_image, style="Dark.TLabel")
    camo_image.image = converted_image  #prevents garbage collection
    camo_image.grid(column=0, row=1, sticky=(W, E))

    instructions = ttk.Label(mainframe, text="Please identify the 'clusters' of colors present in the camouflage", style="Dark.TLabel")
    instructions.grid(column=0, row=0, sticky=(W, E))

    user_n = StringVar()
    dropdown = ttk.Combobox(mainframe, width=5, textvariable=user_n, state="readonly", style="Dark.TCombobox")
    dropdown['values'] = list(range(2, 11))
    dropdown.grid(column=1, row=0, sticky=(W, E))
    dropdown.current(0)

    def enter_command():
        root.quit()

    enter = ttk.Button(mainframe, width=20, text="SUBMIT", command=enter_command, style="Dark.TButton")
    enter.grid(column=2, row=0, sticky=(W, E))
    
    root.mainloop()
    root.destroy()
    return int(user_n.get())




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

#NOTE: silhoette analysis doesn't seem particularly functional nor performative here for estimating the number of colors. Depsite a lot of tweaking i'm getting a lot of inconsistent results as perception is so different than data. The user will be the one deciding how many distinct colors there are per camo.
"""def n_colors_best_fit(array):    #damn this takes a while 

    
    scores = {2:-1.0, 3:-1.0, 4:-1.0, 5:-1.0, 6:-1.0, 7:-1.0, 8:-1.0, 9:-1.0, 10:-1.0}       #this is a crazy expensive operation -- use histogram to make a rough guess within +-1 of estimate?

    lab_array = array_rgb_to_lab(array)

    for n_cluster in scores.keys(): #assumes that any given camo will have between 2 to 10 unique colors.
        clusterer = KMeans(n_clusters=n_cluster, random_state=10)
        cluster_labels = clusterer.fit_predict(lab_array)
        silhouette_avg = silhouette_score(lab_array, cluster_labels)
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
"""

def array_rgb_to_lab(array : np.ndarray) -> np.ndarray: #
    normalized = array.astype(np.float32) / 255.0
    lab_array = ski.color.rgb2lab(normalized)
    return lab_array 

def scaled_lab_values(array):
    scaler = MinMaxScaler()
    return scaler.fit_transform(array)



      
if __name__ == "__main__":
    image = analyze_camo()
    
    n_colors_gui(image)

