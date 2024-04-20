import os
from copy import deepcopy
from urllib.parse import parse_qs
from pathlib import Path

from celery import Celery
from matplotlib import colormaps
import pyvista as pv
from dash import html, dcc, no_update, ctx
from dash import Dash, Patch, Input, Output, State
from dash import CeleryManager
from dash.exceptions import PreventUpdate
import dash_daq as daq
import dash_bootstrap_components as dbc
from dash_vtk.utils import preset_as_options
from dash_pane_split import DashPaneSplit
from dash_breakpoints import WindowBreakpoints

from consts import RepresentationType, RenderMode
from consts import (
    ARTIFACT_STORE_ID,
    VTK_CONTAINER_ID,
    MAIN_CONTAINER_ID,
    URL_LOCATION_ID,
    PLAY_BTN_ID,
    PLAY_INTERVAL_ID,
    TIME_SLIDER_ID,
    RENDER_MODE_DROPDOWN_ID,
    COLOR_MAP_DROPDOWN_ID,
    COLOR_ARRAY_NAME_DROPDOWN_ID,
    REPRESENTATION_TYPE_DROPDOWN_ID,
    OPACITY_SLIDER_ID,
    POINT_SIZE_SLIDER_ID,
    LINE_WIDTH_SLIDER_ID,
    SHOW_SCALAR_BAR_ID,
    BACKGROUND_COLOR_PICKER_ID,
    OPTIONS_STORE_ID,
    ROTATE_X_SLIDER_ID,
    ROTATE_Y_SLIDER_ID,
    MAIN_LOADING_ID,
    RERENDER_LOADING_ID,
    ACTION_STORE_ID,
    CHECKPOINT_STORE_ID,
)
from utils import must_safe_join
from vdisplay import ensure_vdisplay
from timeseries import TimeSeriesMesh
from representation import MeshRepresentation, get_scalar_names

AVIALABLE_CMAPS_INTERACTIVE = [
    i for i in preset_as_options if i["label"] not in ("KAAMS",)
]

AVIALABLE_CMAPS_STATIC = []
for cmap in colormaps:
    try:
        pv.LookupTable(cmap=cmap)
        AVIALABLE_CMAPS_STATIC.append({"label": cmap, "value": cmap})
    except Exception:
        pass


ROOT_PATH = Path(os.getenv("VAR_ROOT", Path(__file__).parent / "examples"))


def get_option(options, name):
    return options.get(str(name), None)


def set_option(options, name, value):
    options[str(name)] = value


def exists_option(options, name):
    return str(name) in options


celery_app = Celery(
    __name__, broker=os.environ["REDIS_URL"], backend=os.environ["REDIS_URL"]
)
background_callback_manager = CeleryManager(celery_app)
app = Dash(
    __name__,
    title="Mesh Viewer",
    compress=True,
    serve_locally=True,
    suppress_callback_exceptions=os.getenv("PROD_ENV") == "true",
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    background_callback_manager=background_callback_manager,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server
if os.getenv("WORK_ROLE") == "worker":
    ensure_vdisplay(force=True)


@app.callback(
    Output("viewport", "data"),
    Input("breakpoints", "width"),
    Input("breakpoints", "height"),
)
def save_viewport(width: str, height: str):
    return {
        "width": width,
        "height": height,
    }


@app.callback(
    [
        RERENDER_LOADING_ID.get_output("children"),
        OPTIONS_STORE_ID.get_output("data"),
        VTK_CONTAINER_ID.get_output("children"),
        COLOR_MAP_DROPDOWN_ID.get_output("options"),
        COLOR_MAP_DROPDOWN_ID.get_output("value"),
        PLAY_INTERVAL_ID.get_output("interval"),
        PLAY_INTERVAL_ID.get_output("disabled"),
    ],
    [
        RENDER_MODE_DROPDOWN_ID.get_input("value"),
        COLOR_ARRAY_NAME_DROPDOWN_ID.get_input("value"),
        COLOR_MAP_DROPDOWN_ID.get_input("value"),
        OPACITY_SLIDER_ID.get_input("value"),
        REPRESENTATION_TYPE_DROPDOWN_ID.get_input("value"),
        POINT_SIZE_SLIDER_ID.get_input("value"),
        LINE_WIDTH_SLIDER_ID.get_input("value"),
        SHOW_SCALAR_BAR_ID.get_input("on"),
        TIME_SLIDER_ID.get_input("value"),
        BACKGROUND_COLOR_PICKER_ID.get_input("value"),
        ROTATE_X_SLIDER_ID.get_input("value"),
        ROTATE_Y_SLIDER_ID.get_input("value"),
        State("viewport", "data"),
        OPTIONS_STORE_ID.get_state("data"),
        PLAY_INTERVAL_ID.get_state("disabled"),
    ],
    running=[
        (
            ACTION_STORE_ID.get_output("data"),
            "disable",
            "ignore",
        ),
    ],
    background=True,
    prevent_initial_call=True,
)
def rerender(
    render_mode,
    color_array_name,
    color_map,
    opacity,
    representation_type,
    point_size,
    line_size,
    show_scalar_bar,
    n_steps,
    background_color,
    rotate_x,
    rotate_y,
    viewport,
    saved_options,
    interval_disabled,
):
    options = Patch()
    artifact = get_option(saved_options, ARTIFACT_STORE_ID)

    if ctx.triggered:
        trigger = ctx.triggered[0]
        trigger_id = trigger["prop_id"].rsplit(".", 1)[0]
        trigger_value = trigger["value"]
        if get_option(saved_options, trigger_id) == trigger_value:
            raise PreventUpdate("No change")
        set_option(options, trigger_id, trigger_value)

    if ctx.triggered_id == RENDER_MODE_DROPDOWN_ID.get_identifier():
        colormaps = (
            AVIALABLE_CMAPS_STATIC
            if render_mode == RenderMode.Static.value
            else AVIALABLE_CMAPS_INTERACTIVE
        )
        color_map = "coolwarm"
        set_option(options, COLOR_MAP_DROPDOWN_ID, color_map)
        interval = 1000 if render_mode == RenderMode.Interactive.value else 1000
    else:
        colormaps = no_update
        interval = no_update

    if not artifact:
        raise PreventUpdate("No artifact specified")

    filepath = must_safe_join(ROOT_PATH, artifact)
    if not filepath.exists():
        raise PreventUpdate("File does not exist")
    color_data_range = None
    if artifact.endswith(".vtm.series"):
        time_series = TimeSeriesMesh(filepath)
        if n_steps >= time_series.n_slices:
            raise PreventUpdate("No more slices")
        grid = time_series.read(n_steps)
        if color_array_name:
            ranges = time_series.get_ranges()
            color_data_range = ranges.get(color_array_name)
    else:
        grid = pv.read(filepath)
    representation = MeshRepresentation(
        grid,
        color_array_name=color_array_name,
        render_mode=render_mode,
        color_map=color_map,
        opacity=opacity,
        rotate_x=rotate_x,
        rotate_y=rotate_y,
        point_size=point_size,
        background_color=background_color["hex"],
        line_width=line_size,
        show_scalar_bar=show_scalar_bar,
        representation_type=representation_type,
    )
    return (
        None,
        options,
        representation.get_view(color_data_range=color_data_range, viewport=viewport),
        colormaps,
        color_map,
        interval,
        interval_disabled,
    )


@app.callback(
    [
        PLAY_INTERVAL_ID.get_output("disabled"),
        CHECKPOINT_STORE_ID.get_output("data"),
    ],
    [
        ACTION_STORE_ID.get_input("data"),
        CHECKPOINT_STORE_ID.get_state("data"),
        PLAY_INTERVAL_ID.get_state("disabled"),
    ],
    prevent_initial_call=True,
)
def hold_play(action, saved, interval_disabled):
    if action == "disable":
        return True, interval_disabled
    else:
        return saved, no_update


@app.callback(
    [
        OPTIONS_STORE_ID.get_output("data"),
        PLAY_INTERVAL_ID.get_output("max_intervals"),
        PLAY_INTERVAL_ID.get_output("n_intervals"),
        PLAY_INTERVAL_ID.get_output("disabled"),
        PLAY_BTN_ID.get_output("children"),
    ],
    [
        PLAY_BTN_ID.get_input("n_clicks"),
        TIME_SLIDER_ID.get_state("value"),
        PLAY_INTERVAL_ID.get_state("disabled"),
        OPTIONS_STORE_ID.get_state("data"),
    ],
    prevent_initial_call=True,
)
def play_time_series(n_clicks, n_steps, interval_disabled, saved_options):
    if not n_clicks:
        raise PreventUpdate("No click")

    artifact = get_option(saved_options, ARTIFACT_STORE_ID)
    if not artifact:
        raise PreventUpdate("No artifact specified")

    filepath = must_safe_join(ROOT_PATH, artifact)
    if not filepath.exists():
        raise PreventUpdate("File does not exist")

    if not artifact.endswith(".vtm.series"):
        raise PreventUpdate("Not a time series")

    time_series = TimeSeriesMesh(filepath)
    if interval_disabled:
        options = Patch()
        n_intervals = n_steps if n_steps < time_series.n_slices - 1 else 0
        set_option(options, PLAY_INTERVAL_ID, n_intervals)
        return (
            options,
            time_series.n_slices,
            n_intervals,
            False,
            html.I(
                className="bi bi-stop-btn-fill",
                disable_n_clicks=True,
                style={
                    "fontSize": "1.5rem",
                    "color": "black",
                },
            ),
        )
    else:
        return (
            no_update,
            no_update,
            no_update,
            True,
            html.I(
                className="bi bi-collection-play-fill",
                disable_n_clicks=True,
                style={
                    "fontSize": "1.5rem",
                    "color": "black",
                },
            ),
        )


@app.callback(
    [
        OPTIONS_STORE_ID.get_output("data"),
        TIME_SLIDER_ID.get_output("value"),
        PLAY_INTERVAL_ID.get_output("n_intervals"),
    ],
    [
        PLAY_INTERVAL_ID.get_input("n_intervals"),
        TIME_SLIDER_ID.get_input("value"),
    ],
    prevent_initial_call=True,
)
def tick_time_series(n_intervals, n_steps):
    options = Patch()

    set_option(options, TIME_SLIDER_ID, n_steps)
    set_option(options, PLAY_INTERVAL_ID, n_intervals)

    if ctx.triggered_id == PLAY_INTERVAL_ID.get_identifier():
        return options, n_intervals, no_update
    else:
        return options, no_update, n_steps


DEFAULT_OPTIONS = {
    str(PLAY_INTERVAL_ID): 0,
    str(RENDER_MODE_DROPDOWN_ID): RenderMode.Interactive.value,
    str(COLOR_MAP_DROPDOWN_ID): "coolwarm",
    str(COLOR_ARRAY_NAME_DROPDOWN_ID): None,
    str(REPRESENTATION_TYPE_DROPDOWN_ID): RepresentationType.Surface.value,
    str(OPACITY_SLIDER_ID): 1.0,
    str(POINT_SIZE_SLIDER_ID): 1,
    str(LINE_WIDTH_SLIDER_ID): 1,
    str(SHOW_SCALAR_BAR_ID): True,
    str(BACKGROUND_COLOR_PICKER_ID): dict(hex="#000000"),
    str(ROTATE_X_SLIDER_ID): 0,
    str(ROTATE_Y_SLIDER_ID): 0,
    str(TIME_SLIDER_ID): 0,
}
app.layout = html.Div(
    [
        WindowBreakpoints(
            id="breakpoints",
        ),
        dcc.Store(id="viewport", storage_type="memory"),
        dcc.Store(id=ACTION_STORE_ID.get_identifier(), storage_type="memory"),
        dcc.Store(id=CHECKPOINT_STORE_ID.get_identifier(), storage_type="memory"),
        dcc.Location(id=URL_LOCATION_ID.get_identifier(), refresh=False),
        dcc.Store(
            id=OPTIONS_STORE_ID.get_identifier(),
            storage_type="memory",
            data=DEFAULT_OPTIONS,
        ),
        dcc.Interval(
            id=PLAY_INTERVAL_ID.get_identifier(),
            n_intervals=DEFAULT_OPTIONS[str(PLAY_INTERVAL_ID)],
            interval=1000,
            max_intervals=0,
            disabled=True,
        ),
        DashPaneSplit(
            id="split",
            mainStyle={"width": "100%", "height": "100%"},
            mainChildren=html.Div(
                [
                    dcc.Loading(
                        type="default",
                        fullscreen=True,
                        children=html.Div(
                            id=MAIN_LOADING_ID.get_identifier(),
                            style={"height": "100%", "width": "100%", "zIndex": 1000},
                        ),
                        style={"height": "100%", "width": "100%"},
                    ),
                    dcc.Loading(
                        type="dot",
                        fullscreen=False,
                        children=html.Div(
                            style={"height": "100%", "width": "100%", "zIndex": 1000},
                            id=RERENDER_LOADING_ID.get_identifier(),
                        ),
                        style={"height": "100%", "width": "100%"},
                    ),
                    html.Div(
                        id=MAIN_CONTAINER_ID.get_identifier(),
                        style={
                            "height": "100%",
                            "width": "100%",
                            "margin": 0,
                            "padding": 0,
                        },
                    ),
                ],
                style={"height": "100%", "width": "100%", "margin": 0, "padding": 0},
            ),
            sidebarTitle="Options",
            sidebarChildren=html.Div(
                [
                    html.Div(
                        [
                            html.Caption("Render Mode"),
                            dcc.Dropdown(
                                id=RENDER_MODE_DROPDOWN_ID.get_identifier(),
                                options=[
                                    {"label": name, "value": option.value}
                                    for name, option in RenderMode.__members__.items()
                                ],
                                value=DEFAULT_OPTIONS[str(RENDER_MODE_DROPDOWN_ID)],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Color Map"),
                            dcc.Dropdown(
                                id=COLOR_MAP_DROPDOWN_ID.get_identifier(),
                                options=[{"label": "coolwarm", "value": "coolwarm"}],
                                value=DEFAULT_OPTIONS[str(COLOR_MAP_DROPDOWN_ID)],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Color Array"),
                            dcc.Dropdown(
                                id=COLOR_ARRAY_NAME_DROPDOWN_ID.get_identifier(),
                                options=[],
                                value=DEFAULT_OPTIONS[
                                    str(COLOR_ARRAY_NAME_DROPDOWN_ID)
                                ],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Representation Type"),
                            dcc.Dropdown(
                                id=REPRESENTATION_TYPE_DROPDOWN_ID.get_identifier(),
                                options=[
                                    {"label": name, "value": option.value}
                                    for name, option in RepresentationType.__members__.items()
                                ],
                                value=DEFAULT_OPTIONS[
                                    str(REPRESENTATION_TYPE_DROPDOWN_ID)
                                ],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Opacity"),
                            daq.Slider(
                                id=OPACITY_SLIDER_ID.get_identifier(),
                                size=215,
                                min=0,
                                max=1,
                                step=0.1,
                                value=DEFAULT_OPTIONS[str(OPACITY_SLIDER_ID)],
                                marks={0: "0", 1: "1.0"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Point Size"),
                            daq.Slider(
                                size=215,
                                id=POINT_SIZE_SLIDER_ID.get_identifier(),
                                min=1,
                                max=10,
                                step=1,
                                value=DEFAULT_OPTIONS[str(POINT_SIZE_SLIDER_ID)],
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Line Size"),
                            daq.Slider(
                                size=215,
                                id=LINE_WIDTH_SLIDER_ID.get_identifier(),
                                min=1,
                                max=10,
                                step=1,
                                value=DEFAULT_OPTIONS[str(LINE_WIDTH_SLIDER_ID)],
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Show Scalar Bar"),
                            daq.BooleanSwitch(
                                id=SHOW_SCALAR_BAR_ID.get_identifier(),
                                on=DEFAULT_OPTIONS[str(SHOW_SCALAR_BAR_ID)],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Rotate X"),
                            daq.Slider(
                                size=215,
                                min=0,
                                max=360,
                                step=1,
                                value=get_option(DEFAULT_OPTIONS, ROTATE_X_SLIDER_ID),
                                id=ROTATE_X_SLIDER_ID.get_identifier(),
                                marks={i: str(i) for i in range(0, 361, 45)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Rotate Y"),
                            daq.Slider(
                                size=215,
                                min=0,
                                max=360,
                                step=1,
                                id=ROTATE_Y_SLIDER_ID.get_identifier(),
                                value=get_option(DEFAULT_OPTIONS, ROTATE_Y_SLIDER_ID),
                                marks={i: str(i) for i in range(0, 361, 45)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Background"),
                            daq.ColorPicker(
                                id=BACKGROUND_COLOR_PICKER_ID.get_identifier(),
                                size=215,
                                value=DEFAULT_OPTIONS[str(BACKGROUND_COLOR_PICKER_ID)],
                            ),
                        ],
                        style={
                            "padding": "1rem 0px",
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "1rem",
                    "padding": "1rem",
                    "paddingTop": "1.5rem",
                },
            ),
            splitMode="vertical",
            panelOrder="mainFirst",
            sidebarMaxSize=250,
            sidebarDefaultSize=250,
            sidebarMinSize=250,
        ),
    ],
    style={"height": "100vh", "width": "100%", "margin": 0, "padding": 0},
)


@app.callback(
    [
        MAIN_LOADING_ID.get_output("children"),
        OPTIONS_STORE_ID.get_output("data"),
        MAIN_CONTAINER_ID.get_output("children"),
        COLOR_ARRAY_NAME_DROPDOWN_ID.get_output("options"),
        COLOR_ARRAY_NAME_DROPDOWN_ID.get_output("value"),
        RENDER_MODE_DROPDOWN_ID.get_output("value"),
        RENDER_MODE_DROPDOWN_ID.get_output("disabled"),
        COLOR_MAP_DROPDOWN_ID.get_output("options"),
        PLAY_INTERVAL_ID.get_output("interval"),
    ],
    [
        URL_LOCATION_ID.get_input("search"),
        State("viewport", "data"),
    ],
    background=True,
    prevent_initial_call=True,
)
def viewer(search, viewport):
    qs = parse_qs(search.lstrip("?"))
    artifacts = qs.get("artifact")
    if not artifacts:
        raise PreventUpdate("No artifact specified")

    artifact = artifacts[0]
    filepath = must_safe_join(ROOT_PATH, artifact)
    if not filepath.exists():
        raise PreventUpdate("File does not exist")

    options = deepcopy(DEFAULT_OPTIONS)

    set_option(options, ARTIFACT_STORE_ID, artifact)
    set_option(options, TIME_SLIDER_ID, 0)

    color_data_range = None
    color_array_name = None
    array_names = []
    if artifact.endswith(".vtm.series"):
        time_series = TimeSeriesMesh(filepath)
        grid = time_series.read(0)
        array_names = get_scalar_names(grid)
        if array_names:
            color_array_name = array_names[0]
            ranges = time_series.get_ranges()
            color_data_range = ranges.get(color_array_name)
    else:
        grid = pv.read(filepath)
        array_names = get_scalar_names(grid)
        if array_names:
            color_array_name = array_names[0]
    set_option(options, COLOR_ARRAY_NAME_DROPDOWN_ID, color_array_name)

    if grid.actual_memory_size > 1024 * 50:  # 50MB
        render_mode = RenderMode.Static.value
    else:
        render_mode = RenderMode.Interactive.value

    interval = 1000 if render_mode == RenderMode.Interactive.value else 1000
    colormaps = (
        AVIALABLE_CMAPS_STATIC
        if render_mode == RenderMode.Static.value
        else AVIALABLE_CMAPS_INTERACTIVE
    )
    set_option(options, RENDER_MODE_DROPDOWN_ID, render_mode)

    representation = MeshRepresentation(
        grid,
        render_mode=render_mode,
        color_array_name=color_array_name,
        background_color=options[str(BACKGROUND_COLOR_PICKER_ID)]["hex"],
    )
    vtk_view = representation.get_view(
        color_data_range=color_data_range, viewport=viewport
    )
    if artifact.endswith(".vtm.series"):
        vtk_view.style["height"] = "calc(100vh - 2rem)"
        main_view = html.Div(
            [
                dbc.Row(
                    [
                        html.Div(
                            dbc.Button(
                                html.I(
                                    className="bi bi-collection-play-fill",
                                    disable_n_clicks=True,
                                    style={
                                        "fontSize": "1.5rem",
                                        "color": "black",
                                    },
                                ),
                                id=PLAY_BTN_ID.get_identifier(),
                                className="d-flex align-items-center",
                                color="link",
                            ),
                            style={
                                "width": "3rem",
                                "marginLeft": "1rem",
                                "marginRight": "1rem",
                            },
                        ),
                        html.Div(
                            daq.Slider(
                                id=TIME_SLIDER_ID.get_identifier(),
                                min=0,
                                step=1,
                                size=len(time_series.info["files"]) * 35,
                                targets={
                                    i: str(time_series.info["files"][i]["time"])
                                    for i in range(time_series.n_slices)
                                },
                                value=get_option(DEFAULT_OPTIONS, TIME_SLIDER_ID),
                                max=time_series.n_slices - 1,
                            ),
                            style={
                                "overflowX": "scroll",
                                "paddingTop": "1.5rem",
                            },
                        ),
                    ],
                    style={
                        "height": "3.5rem",
                        "paddingTop": ".5rem",
                        "width": "100%",
                        "display": "flex",
                        "flexDirection": "row",
                        "flexWrap": "nowrap",
                    },
                ),
                dbc.Row(
                    vtk_view,
                    style={
                        "margin": 0,
                        "padding": 0,
                        "height": "100%",
                        "width": "100%",
                    },
                    id=VTK_CONTAINER_ID.get_identifier(),
                ),
            ],
            style={"height": "100%", "margin": 0, "padding": 0, "width": "100%"},
        )
    else:
        main_view = html.Div(
            [
                html.Div(
                    vtk_view,
                    id=VTK_CONTAINER_ID.get_identifier(),
                    style={
                        "height": "100%",
                        "width": "100%",
                        "margin": 0,
                        "padding": 0,
                    },
                ),
                html.Div(
                    [
                        dcc.Slider(
                            min=0,
                            max=1,
                            step=0.01,
                            value=get_option(options, TIME_SLIDER_ID),
                            id=TIME_SLIDER_ID.get_identifier(),
                        ),
                    ],
                    style={"display": "none"},
                ),
            ],
            style={"height": "100%", "width": "100%", "margin": 0, "padding": 0},
        )

    return (
        None,
        options,
        main_view,
        [{"label": name, "value": name} for name in array_names],
        color_array_name,
        render_mode,
        False,
        colormaps,
        interval,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
