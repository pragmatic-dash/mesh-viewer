from enum import Enum

from dash_id_utils import DashIDGenerator, DashIDWrapper


class RepresentationType(Enum):
    Points = 0
    Wireframe = 1
    Surface = 2


class RenderMode(Enum):
    Static = "static"
    Interactive = "interactive"


VTK_VIEW_ID = DashIDGenerator(type="view", name="vtk-view")
VTK_CONTAINER_ID = DashIDGenerator(type="view", name="vtk-container")
MAIN_CONTAINER_ID = DashIDGenerator(type="view", name="main")
MAIN_LOADING_ID = DashIDGenerator(type="loading", name="main")
RERENDER_LOADING_ID = DashIDGenerator(type="loading", name="rerender")
COLOR_MAP_VIEW_ID = DashIDGenerator(type="view", name="color-map")

URL_LOCATION_ID = DashIDGenerator(type="location", name="url")
PLAY_BTN_ID = DashIDGenerator(type="button", name="play")

ARTIFACT_STORE_ID = DashIDGenerator(type="store", name="artifact")
OPTIONS_STORE_ID = DashIDGenerator(type="store", name="options")
ACTION_STORE_ID = DashIDWrapper(
    "action"
)  # Use DashIDWrapper to avoid Dash's bug with `runnig` attribute
CHECKPOINT_STORE_ID = DashIDGenerator(type="store", name="checkpoint")


PLAY_INTERVAL_ID = DashIDGenerator(type="interval", name="play")
TIME_SLIDER_ID = DashIDGenerator(type="slider", name="time")
ROTATE_X_SLIDER_ID = DashIDGenerator(type="slider", name="rotate-x")
ROTATE_Y_SLIDER_ID = DashIDGenerator(type="slider", name="rotate-y")

RENDER_MODE_DROPDOWN_ID = DashIDGenerator(type="dropdown", name="render-mode")
COLOR_MAP_DROPDOWN_ID = DashIDGenerator(type="dropdown", name="color-map")
COLOR_ARRAY_NAME_DROPDOWN_ID = DashIDGenerator(type="dropdown", name="color-array-name")
REPRESENTATION_TYPE_DROPDOWN_ID = DashIDGenerator(
    type="dropdown", name="representation-type"
)
OPACITY_SLIDER_ID = DashIDGenerator(type="slider", name="opacity")
POINT_SIZE_SLIDER_ID = DashIDGenerator(type="slider", name="point-size")
LINE_WIDTH_SLIDER_ID = DashIDGenerator(type="slider", name="line-width")
SHOW_SCALAR_BAR_ID = DashIDGenerator(type="checkbox", name="show-scalar-bar")
BACKGROUND_COLOR_PICKER_ID = DashIDGenerator(
    type="color-picker", name="background-color"
)
