import os

import sh
import pyvista as pv


def ensure_vdisplay(force=True):
    if os.getenv("DISPLAY") is None or force:
        try:
            sh.pgrep("Xvfb")
        except sh.ErrorReturnCode:
            pv.start_xvfb(wait=0.1, window_size=(4096, 2160))
        os.environ["DISPLAY"] = ":99"
