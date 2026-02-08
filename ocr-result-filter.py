import json, copy, sys



prev_x = -999
prev_y = -999
FILENAME = sys.argv[1]

# SAN - NYC: -118, -73.5, 30, 41, ~0.00025
# SEA - YYZ: -124, -122, 47.4, 49.5
# SYR - MIA: -81.886137, -75.596041, 25.559101, 43.332030
# (day 1: south 36.070611)
# 2023 summer: -80.596513, -73.327364, 38.318572, 43.376792
# SAN-YYZ: -124.277839, -116.511427, 31.912739, 49.448938
# 2023 Lake Placid: -76.346686, -73.646463, 40.374249, 45.018334, 
# 2024 Eclipse: -76.397332, -71.992911, 42.591147, 45.033079

# Bounds: long, long, lat, lat
bounds = [-76.397332, -71.992911, 42.591147, 45.033079]
# Expected differences in long/lat between two consecutive measures
coeff = 0.0005


import numpy as np
from scipy.ndimage import gaussian_filter1d

def smooth_points(points, sigma=1.0):
    arr = np.array(points, dtype=float)
    xs = gaussian_filter1d(arr[:,0], sigma=sigma)
    ys = gaussian_filter1d(arr[:,1], sigma=sigma)
    return list(zip(xs, ys))

last_good_x = -999
last_good_y = -999
skipped = 1
with open(FILENAME) as f:
    j = json.load(f)
    j2 = copy.deepcopy(j)
    j2["geometry"]["coordinates"] = []
    for e in j["geometry"]["coordinates"]:
        print(e)
        if (e[0] >= min(bounds[0], bounds[1]) and e[0] <= max(bounds[0], bounds[1]) and e[1] >= min(bounds[2], bounds[3]) and e[1] <= max(bounds[2], bounds[3])):
            if prev_x == -999 and prev_y == -999:
                prev_x = e[0]
                prev_y = e[1]
            if abs(e[0] - prev_x) < coeff * skipped and abs(e[1] - prev_y) < coeff * skipped:
                j2["geometry"]["coordinates"].append(e)
                prev_x = e[0]
                prev_y = e[1]
                skipped = 1
            else:
                skipped += 1


j2["geometry"]["coordinates"] = smooth_points(j2["geometry"]["coordinates"], sigma=2)
with open(f"{FILENAME}-new.geojson", "w") as f:
    json.dump(j2, f)