import json
import sys
from pathlib import Path
from functools import cached_property

import pyvista as pv

from utils import merge_vtk_datasets


class TimeSeriesMesh:

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.root = self.filepath.parent
        self.filename = filepath.name

    @cached_property
    def info(self):
        with self.filepath.open() as f:
            return json.load(f)

    @property
    def n_slices(self):
        return len(self.info["files"])

    def read_blocks(self, slice: int = 0):
        info = self.info
        if len(info["files"]) <= slice:
            raise ValueError(f"Slice {slice} does not exist")

        filename = info["files"][slice]["name"]
        slice_file = self.root / filename
        return pv.read(slice_file)

    def read(self, slice: int = 0, scalars=None):
        blocks = self.read_blocks(slice)
        return merge_vtk_datasets(blocks, scalars=scalars)

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
            grid, _ = self.read(i)
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
