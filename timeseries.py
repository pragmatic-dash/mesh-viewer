import json
import sys
from typing import List
from pathlib import Path
from functools import cached_property

import pyvista as pv


class TimeSeriesMesh:

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.root = self.filepath.parent
        self.filename = filepath.name

    @classmethod
    def merge_datasets(cls, datasets):
        if isinstance(datasets, pv.MultiBlock):
            return pv.merge(
                [cls.merge_datasets(datasets[name]) for name in datasets.keys()]
            )
        else:
            return datasets

    @cached_property
    def info(self):
        with self.filepath.open() as f:
            return json.load(f)

    @property
    def n_slices(self):
        return len(self.info["files"])

    def read(self, slice: int = 0):
        info = self.info
        if len(info["files"]) <= slice:
            raise ValueError(f"Slice {slice} does not exist")

        filename = info["files"][slice]["name"]
        slice_file = self.root / filename
        grid = pv.read(slice_file)
        return self.merge_datasets(grid)

    def get_ranges(self):
        range_cache_filepath = self.root / ".ranges.json"
        if range_cache_filepath.exists():
            with range_cache_filepath.open() as f:
                cached = json.load(f)
            if cached["n_slices"] == self.n_slices:
                return cached["ranges"]
        ranges = self.compute_ranges()
        self.save_ranges(ranges)
        return ranges

    def save_ranges(self, ranges):
        range_cache_filepath = self.root / ".ranges.json"
        with range_cache_filepath.open("w") as f:
            json.dump({"n_slices": self.n_slices, "ranges": ranges}, f, indent=2)

    def compute_ranges(self):
        ranges = {}
        for i in range(self.n_slices):
            grid = self.read(i)
            array_names = grid.point_data.keys() + grid.cell_data.keys()
            for name in array_names:
                min_val, max_val = ranges.get(name) or [
                    sys.float_info.max,
                    -sys.float_info.max,
                ]
                min_val = float(min(min_val, grid[name].min()))
                max_val = float(max(max_val, grid[name].max()))
                ranges[name] = [min_val, max_val]
        return ranges