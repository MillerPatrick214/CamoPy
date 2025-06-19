import ctypes
import functools
from operator import index
from unittest import result
import skimage as ski
import numpy as np
import time

#Debug test 
test_rgb_array = np.array([
    [(255, 0, 0), 10],       # Bright Red
    [(254, 1, 1), 5],        # Slightly off Red
    [(0, 255, 0), 15],       # Bright Green
    [(1, 254, 1), 8],        # Slightly off Green
    [(0, 0, 255), 20],       # Bright Blue
    [(1, 1, 254), 10],       # Slightly off Blue
    [(255, 255, 0), 7],      # Yellow
    [(254, 254, 1), 12],     # Slightly off Yellow
    [(255, 165, 0), 9],      # Orange
    [(254, 164, 0), 6],      # Slightly off Orange
    [(128, 0, 128), 13],     # Purple
    [(127, 0, 127), 4],      # Slightly off Purple
    [(255, 192, 203), 11],   # Pink
    [(254, 191, 202), 3],    # Slightly off Pink
    [(128, 128, 128), 10],   # Gray
    [(129, 129, 129), 5],    # Slightly off Gray    [(255, 255, 255), 8],    # White
    [(254, 254, 254), 2],    # Slightly off White
    [(0, 0, 0), 30],         # Black
    [(1, 1, 1), 10],         # Slightly off Black
    [(123, 50, 150), 7],     # Random unique color
    [(124, 51, 151), 2]      # Slightly off Random unique color
], dtype=object)

class Stratify:
    def stopwatch(func):
        @functools.wraps(func)
        def wrapper_timer(*args, **kwargs):
            print(f"Calling {func.__name__}...")
            start_time = time.perf_counter()
            value = func(*args, **kwargs)
            end_time = time.perf_counter()
            runtime = end_time - start_time
            print(f"Finished {func.__name__}() in {runtime:.4f} secs")
            return value
        return wrapper_timer
    

    @staticmethod
    @stopwatch
    def color_refine_py(input_array : np.ndarray, threshold : int = 25) -> np.ndarray:
        dll = ctypes.CDLL('./quick-refine/x64/Release/quick-refine.dll')

        dll.color_refine.argtypes = [
            ctypes.POINTER(ctypes.c_float), #input_array
            ctypes.c_int,                   #input_size
            ctypes.c_int,                   #threshold for CIED
            ctypes.POINTER(ctypes.c_int),   #pass by ref for output size
            ctypes.POINTER(ctypes.c_float)  #pass by ref for output array
        ]

        dll.color_refine.restype = ctypes.c_voidp 

        flat_list = []
        for item in input_array:
            lab_color = item[0]
            count = item[1]
            flat_list.extend([lab_color[0], lab_color[1], lab_color[2], count])
        
        input_size = len(input_array)
        flat_array = (ctypes.c_float * len(flat_list))(*flat_list)
        max_output_size = input_size * 4
        output_array = (ctypes.c_float * max_output_size)()

        output_size = ctypes.c_int(0)

        dll.color_refine(
            flat_array,
            input_size,
            threshold,
            ctypes.byref(output_size),
            output_array
        )

        actual_output_size = output_size.value
        if actual_output_size == 0:
            return np.array([], dtype=object).reshape(0, 2)
        
        result_list = []
        for i in range(actual_output_size):
            result_list.append([
                (output_array[i * 4], output_array[(i * 4) + 1], output_array[(i * 4) + 2]), 
                output_array[(i * 4) + 3]])
            
        return np.array(result_list, dtype=object)
            

    @staticmethod
    def rgbarr_to_labarr(array : np.ndarray) -> np.ndarray:
        print(array[:, 0])

        values = np.stack(array[:, 0]) /255.0 #normalizes and stacks the array. I guess rgb must be from 0-1 not 0-255 hahaha
    
        replacement_col = ski.color.rgb2lab(values, illuminant='D65', observer='2', channel_axis=-1)
        array[:, 0] = [tuple(lab) for lab in replacement_col]


        return array

    
    @staticmethod
    @stopwatch
    def refine(lab_array :np.ndarray, threshold=10, count=1) ->np.ndarray: #This is only O(n) so it should be literally expontentially better. Less memory overhang too without recursion. Only issue that this requires a properly sorted list. So It would be O(n) +  O for whatever sort. Additionally sort would have to be ordered by ciede2000. 
        from collections import defaultdict

        print("refine prior size " + str(len(lab_array)))

        curr_color = lab_array[0, 0]
        refined_list = []
        counter = lab_array[0, 1]
        i = 1
        refined_list.append((curr_color, counter))

        while i < len(lab_array):
            delta = ski.color.deltaE_ciede2000(curr_color, lab_array[i, 0])
            if delta > threshold:
                refined_list.append((curr_color, counter))
                curr_color = lab_array[i, 0]
                counter =  lab_array[i, 1]
            else:
                counter += lab_array[i, 1]
            i += 1
        refined_list.append((curr_color, counter))  # Add this line

        print("refine new size " + str(len(refined_list)))
        return np.array(refined_list, dtype=object)


    @staticmethod
    def labarr_to_rgbarr(array : np.ndarray) -> np.ndarray:
        print(array[:, 0])

        values = np.stack(array[:, 0])
    
        replacement_col = ski.color.lab2rgb(values, illuminant='D65', observer='2', channel_axis=-1)
        replacement_col = (replacement_col * 255).astype(int)
        replacement_col = np.clip(replacement_col, 0, 255)  #make sure we're not exceeding expected RBG values here. There is some slush in the conversion process.

        array[:, 0] = [tuple(lab) for lab in replacement_col]

        return array

    
    @staticmethod
    @stopwatch
    def lab_sort(lab_array : np.ndarray) -> np.ndarray:
        l_vals = np.array([color[0] for color in lab_array[:, 0]])
        a_vals = np.array([color[1] for color in lab_array[:, 0]])
        b_vals = np.array([color[2] for color in lab_array[:, 0]])

        sort_indices = np.lexsort((b_vals, a_vals, l_vals))
        sorted_array = lab_array[sort_indices]
    
        return sorted_array
        
 
    @staticmethod
    def stratify(rgb_array : np.ndarray) -> np.ndarray:   
        lab_array = Stratify.rgbarr_to_labarr(rgb_array)
        #lab_array_sorted = Stratify.lab_sort(lab_array)
        color_strata = Stratify.color_refine_py(lab_array)
        strata_array = Stratify.labarr_to_rgbarr(color_strata)
        print(f"Stratify array return type: {type(strata_array)}")

        with open("sortedarray.txt", "w+") as txt:
            for element in strata_array:
                txt.write(f"{element}\n")

        return strata_array
    
    

#Debug test
if __name__ == "__main__":
    test_arr = Stratify.stratify(test_rgb_array)
