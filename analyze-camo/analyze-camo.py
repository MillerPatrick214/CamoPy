from os import listdir
import json
import numpy as np
import ctypes
import skimage as ski
from PIL import Image
import numpy as np

def rgb_to_hex(color : tuple):
    #print(f"rgb_to_hex: input recieved type: {type(color)}" )
    red, green, blue = color
    return '#%02x%02x%02x' % (int(red), int(green), int(blue))

def analyze_camo() -> None:
    #json = json_load("./analyze-camo/camo-data.json")
    camoset_dir = "./analyze-camo/camoset"
    for image in listdir(camoset_dir):
        print ("test")
        if (image.endswith((".png", ".jpg",".jpeg"))):
            print('reeee')
            with Image.open(f"{camoset_dir}/{image}") as img:
                img = img.convert("RGB")
                img_array = np.array(img, dtype = np.float32) / 255.0 #normalize these hoes
                print(img_array)
                height, width, bands = img_array.shape
                flat_array = img_array.reshape(height * width, bands) #collapse height and width to make 2 d (pixels, bands)
                flat_array = ski.color.rgb2lab(flat_array, illuminant="D65", observer="2")
                flat_array = np.unique(flat_array, axis=0)
                np.savetxt('flat_array.txt', flat_array, fmt="%1.3f")


def refine_call(array : np.ndarray) -> np.ndarray:
    dll = ctypes.CDLL("./analyze-camo/camo-api-refine.dll")
    
    dll.color_refine.argtypes = [
          ctypes.POINTER(ctypes.c_float), #input_array
          ctypes.c_int,                   #input_size
          ctypes.c_int,                   #threshold for CIED
          ctypes.POINTER(ctypes.c_int),   #pass by ref for output size
          ctypes.POINTER(ctypes.c_float)  #pass by ref for output array
      ]
    
    dll.color_refine.restype = ctypes.c_voidp

    flat_list = []
    for element in array:
      flat_list.extend(element[0], element[1], element[2])

    input_size = len(array)
    flat_array = (ctypes.c_float * len(flat_list))(*flat_list)
    max_output_size = input_size * 3
    output_array = (ctypes.c_float * max_output_size)()
    output_size = ctypes.c_int(0)
    threshold = 5 #may need to be adjusted down. The reason why we have to do any of this crap is due to compression on images screwing up colors. This may benefit by the "bucket" approach I was thinking about w/ note in stratify

    dll.color_refine(
            flat_array,
            input_size,
            threshold,
            ctypes.byref(output_size),
            output_array
        )
    
    result_array = np.array(output_array)
    result_array = result_array.reshape(3, -1)
    print("result_array: " + str(result_array))
    result_array = ski.color.lab2rgb(result_array)
    result_array = (result_array * 255).astype(int)
    result_list = [map(lambda element : rgb_to_hex(element))]
    with open('flat_array.txt', "w+") as txt:
        for hex in result_list:
            txt.writelines(result_list, "\n")
      
if __name__ == "__main__":
    analyze_camo()