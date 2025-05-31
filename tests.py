import numpy as np

import numpy as np

a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
stacked = np.stack((a, b), axis=1)
print(stacked)