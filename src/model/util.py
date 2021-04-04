import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

data_folder_path = Path(__file__).parent.parent.absolute() / 'data'


def eq_all(x: np.array, y: np.array):
    return (x == y).all()


class Loc:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def haversine_distance(self, other):
        """
        Get the haversine distance in km.

        :param other: another location
        :return: haversine distance between self and other
        """
        if self == other:
            return 0.0

        v = (math.sin(self.lat * math.pi / 180) * math.sin(other.lat * math.pi / 180)
             + math.cos(self.lat * math.pi / 180) * math.cos(other.lat * math.pi / 180)
             * math.cos(other.lon * math.pi / 180 - self.lon * math.pi / 180))

        # take care of floating point imprecision
        if 1.0 < v < 1.01:
            v = 1.0
        elif -1.01 < v < -1.0:
            v = -1.0

        if v < -1 or v > 1:
            raise Exception('Error in distance for %s and %s' % (self, other))

        return 6378 * math.acos(v)

    def __iter__(self):
        yield self.lat
        yield self.lon


usa_zips = pd.read_csv(data_folder_path / 'USA_zips.csv')
usa_zips.columns = usa_zips.columns.str.lower()


def get_random_us_locs(n):
    ret = usa_zips.sample(n)
    ret.index = range(len(ret))
    return ret
