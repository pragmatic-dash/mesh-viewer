import os
from pathlib import Path
from typing import Union


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
