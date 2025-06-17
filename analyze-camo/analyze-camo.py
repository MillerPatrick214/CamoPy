from os import listdir
import json
from PIL import Image
import numpy as np



def analyze_camo() -> None:
    #json = json_load("./analyze-camo/camo-data.json")
    camoset_dir = "./analyze-camo/camoset"
    for image in listdir(camoset_dir):
        print ("test")
        if (image.endswith((".png", ".jpg",".jpeg"))):
            print('reeee')
            with Image.open(f"{camoset_dir}\{image}") as img:
                img = img.convert("RGB")
                img_array = np.array(img, dtype = np.uint8)
                print(img_array)
                height, width, bands = img_array.shape
                flat_array = img_array.reshape(height * width, bands) #collapse height and width to make 2 d (pixels, bands)
                np.savetxt('stackedshit.txt', flat_array, fmt="%d")
                flat_array = np.unique(flat_array, axis=0)
                np.savetxt('unique_arrays.txt', flat_array, fmt="%d")
                
if __name__ == "__main__":
    analyze_camo()