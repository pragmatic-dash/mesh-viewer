import os
from pathlib import Path
from typing import Union

import pyvista as pv


def must_safe_join(
    base_dir: Union[str, Path], sub_path: Union[str, Path], *, allow_subpath_empty=False
) -> Path:
    base_dir = str(base_dir)
    sub_path = str(sub_path)

    base_dir = os.path.abspath(base_dir)
    sub_path = os.path.normpath(sub_path)

    final_path = os.path.abspath(os.path.join(base_dir, sub_path))
    common_prefix = os.path.commonprefix([base_dir, final_path])
    if final_path == base_dir and not allow_subpath_empty:
        raise Exception("Malicious path detected")
    elif common_prefix == base_dir:
        return Path(final_path)
    else:
        raise Exception("Malicious path detected")


def get_scalar_names(grid):
    if isinstance(grid, pv.MultiBlock):
        names = []
        for block in grid:
            names.extend(get_scalar_names(block))
        return list(sorted(set(names)))
    return list(sorted(set(grid.point_data.keys() + grid.cell_data.keys())))


def merge_vtk_datasets(datasets, scalars=None):
    if scalars is None:
        scalars = get_scalar_names(datasets)
    elif not isinstance(scalars, list):
        scalars = [scalars]
    scalars = [i.split("#")[0] for i in scalars]

    array_names = []
    grid, has_missing = _merge_vtk_datasets(datasets, scalars=scalars)
    if grid:
        if isinstance(grid, pv.PolyData):
            for name in get_scalar_names(grid):
                data_array = grid.get_array(name)
                ndim = data_array.shape[1] if data_array.ndim > 1 else 1
                if ndim == 1:
                    array_names.append(name)
                    continue
                for i in range(ndim):
                    array_names.append(f"{name}#{i}")
                    if name in grid.point_data:
                        grid.point_data.set_array(data_array[:, i], f"{name}#{i}")
                    elif name in grid.cell_data:
                        grid.cell_data.set_array(data_array[:, i], f"{name}#{i}")
                if name in grid.point_data:
                    grid.point_data.remove(name)
                elif name in grid.cell_data:
                    grid.cell_data.remove(name)
        else:
            array_names = get_scalar_names(grid)
    return (
        array_names,
        grid,
        has_missing,
    )


def _merge_vtk_datasets(datasets, scalars):
    if isinstance(datasets, pv.MultiBlock):
        has_missing = False
        blocks = []
        for name in datasets.keys():
            block, _has_missing = _merge_vtk_datasets(datasets[name], scalars=scalars)
            has_missing = has_missing or _has_missing
            if block:
                blocks.append(block)
        if not blocks:
            return None, has_missing
        return pv.merge(blocks), has_missing
    elif len(scalars) == 0:
        return datasets, False
    elif set(scalars) <= set(datasets.array_names):
        return datasets, False
    return None, True
