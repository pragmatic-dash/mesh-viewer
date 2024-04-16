import pyvista as pv

from dash import html, dcc, Input, Output, Patch
from dash_vtk.utils import to_mesh_state, preset_as_options
import dash_bootstrap_components as dbc
import dash
import dash_vtk
import dash_daq as daq
from dash_pane_split import DashPaneSplit
from matplotlib import colors

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


grid = pv.read("examples/simple.vtk")
RepresentationType = {
    "Points": 0,
    "Wireframe": 1,
    "Surface": 2,
}


def get_geometry_representation(
    color_array_name="T",
    color_map="Cool to Warm",
    opacity=1,
    point_size=1,
    line_width=1,
    show_scalar_bar=True,
    representation=RepresentationType["Surface"],
):
    color_array_name = color_array_name or grid.array_names[0]
    mesh_state = to_mesh_state(grid, color_array_name)
    return dash_vtk.GeometryRepresentation(
        [
            dash_vtk.Mesh(state=mesh_state, id="mesh"),
        ],
        id="repr",
        showScalarBar=show_scalar_bar,
        scalarBarTitle=color_array_name,
        mapper={
            "scalarMode": 3,
            "colorByArrayName": color_array_name,
            "scalarVisibility": True,
            "interpolateScalarsBeforeMapping": True,
        },
        actor={},
        colorMapPreset=color_map,
        colorDataRange=mesh_state["field"]["dataRange"],
        property={
            "edgeVisibility": False,
            "pointSize": point_size,
            "lineWidth": line_width,
            "opacity": opacity,
            "representation": representation,
        },
    )


vtk_view = dash_vtk.View(
    id="vtk-view",
    background=colors.hex2color("#CFDEE3"),
    children=[get_geometry_representation()],
)


@app.callback(
    Output("vtk-view", "children"),
    Input("color-array", "value"),
    Input("color-map", "value"),
    Input("opacity", "value"),
    Input("representation", "value"),
    Input("point-size", "value"),
    Input("line-size", "value"),
    Input("scalar-bar", "on"),
    prevent_initial_call=True,
)
def update_render_options(
    color_array_name,
    color_map,
    opacity,
    representation,
    point_size,
    line_size,
    show_scalar_bar,
):
    return [
        get_geometry_representation(
            color_array_name=color_array_name,
            color_map=color_map,
            opacity=opacity,
            representation=representation,
            point_size=point_size,
            line_width=line_size,
            show_scalar_bar=show_scalar_bar,
        )
    ]


@app.callback(
    Output("vtk-view", "background"),
    Output("vtk-view", "triggerRender"),
    Input("vtk-view", "triggerRender"),
    Input("background", "value"),
    prevent_initial_call=True,
)
def update_background(render_count, background):
    print(background)
    rgb = background["rgb"]
    return [rgb["r"] / 255, rgb["g"] / 255, rgb["b"] / 255, rgb["a"]], (
        render_count or 0
    ) + 1


app.layout = html.Div(
    [
        DashPaneSplit(
            id="split",
            mainStyle={"width": "100%", "height": "100%"},
            mainChildren=[
                vtk_view,
            ],
            sidebarTitle="Options",
            sidebarChildren=html.Div(
                [
                    html.Div(
                        [
                            html.Caption("Color Map"),
                            dcc.Dropdown(
                                id="color-map",
                                options=preset_as_options,
                                value="Cool to Warm",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Color Array"),
                            dcc.Dropdown(
                                id="color-array",
                                options=[
                                    {"label": name, "value": name}
                                    for name in grid.array_names
                                ],
                                value=grid.array_names[0],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Representation"),
                            dcc.Dropdown(
                                id="representation",
                                options=[
                                    {"label": name, "value": value}
                                    for name, value in RepresentationType.items()
                                ],
                                value=RepresentationType["Surface"],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Opacity"),
                            daq.Slider(
                                id="opacity",
                                size=215,
                                min=0,
                                max=1,
                                step=0.1,
                                value=1,
                                marks={0: "0", 1: "1.0"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Point Size"),
                            daq.Slider(
                                size=215,
                                id="point-size",
                                min=1,
                                max=10,
                                step=1,
                                value=1,
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Line Size"),
                            daq.Slider(
                                size=215,
                                id="line-size",
                                min=1,
                                max=10,
                                step=1,
                                value=1,
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Show Scalar Bar"),
                            daq.BooleanSwitch(
                                id="scalar-bar",
                                on=True,
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                    html.Div(
                        [
                            html.Caption("Background"),
                            daq.ColorPicker(
                                id="background",
                                size=215,
                                value=dict(hex="#CFDEE3"),
                            ),
                        ],
                        style={
                            "padding": "1rem 0px",
                            "display": "flex",
                            "flex-direction": "column",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flex-direction": "column",
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
        )
    ],
    style={"height": "100vh", "width": "100%"},
)


if __name__ == "__main__":
    app.run_server(debug=True)
