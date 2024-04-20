import base64
from PIL import Image
from io import BytesIO

from matplotlib import colors
import pyvista as pv
from dash import html
from dash_vtk import GeometryRepresentation, Mesh, View
from dash_vtk.utils import to_mesh_state
from dash_fullscreen import DashFullscreen

from consts import RepresentationType, RenderMode
from consts import VTK_VIEW_ID


def get_scalar_names(grid):
    return grid.point_data.keys() + grid.cell_data.keys()


def numpy_to_base64(image_array):
    image = Image.fromarray(image_array)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    base64_bytes = base64.b64encode(image_bytes)
    return base64_bytes.decode("utf-8")


class MeshRepresentation:

    def __init__(
        self,
        grid,
        color_array_name=None,
        color_map=None,
        opacity=1.0,
        point_size=1,
        line_width=1,
        show_scalar_bar=True,
        rotate_x=None,
        rotate_y=None,
        background_color="#000000",
        render_mode=RenderMode.Interactive.value,
        representation_type=RepresentationType.Surface.value,
    ):
        self.grid = grid
        self.color_array_name = color_array_name
        self.color_map = color_map
        self.opacity = opacity
        self.point_size = point_size
        self.background_color = background_color
        self.rotate_x = rotate_x
        self.rotate_y = rotate_y
        self.render_mode = render_mode
        self.line_width = line_width
        self.show_scalar_bar = show_scalar_bar
        self.representation_type = representation_type

    def get_view(self, color_data_range=None, viewport=None):
        color_array_name = self.color_array_name

        color_map = self.color_map or "coolwarm"

        grid = self.grid
        if not color_data_range and color_array_name:
            color_data_range = grid.get_data_range(color_array_name)

        if self.rotate_x:
            grid.rotate_x(self.rotate_x, inplace=True)
        if self.rotate_y:
            grid.rotate_y(self.rotate_y, inplace=True)

        if self.render_mode == "static":
            plotter = pv.Plotter(off_screen=True)
            plotter.add_mesh(
                grid,
                opacity=self.opacity,
                style=RepresentationType(self.representation_type).name.lower(),
                lighting=True,
                cmap=color_map,
                scalars=color_array_name,
                clim=color_data_range,
                point_size=self.point_size,
                line_width=self.line_width,
                show_scalar_bar=self.show_scalar_bar,
                scalar_bar_args=dict(
                    title=color_array_name,
                    vertical=True,
                    color="white",
                    nan_annotation=True,
                    shadow=True,
                ),
                interpolate_before_map=True,
            )
            plotter.background_color = self.background_color
            window_size = None
            if viewport:
                window_size = (viewport["width"] - 250, viewport["height"])
            image = plotter.screenshot(
                None,
                return_img=True,
                transparent_background=False,
                window_size=window_size,
            )
            plotter.close()
            image_base64 = numpy_to_base64(image)
            return html.Div(
                DashFullscreen(
                    html.Img(
                        src=f"data:image/png;base64,{image_base64}",
                        style={"height": "100%", "maxWidth": "calc(100vw - 250px"},
                    ),
                    style={"height": "100%"},
                ),
                id=VTK_VIEW_ID.get_identifier(),
                style={
                    "height": "100%",
                    "margin": 0,
                    "padding": 0,
                    "textAlign": "center",
                    "backgroundColor": self.background_color,
                },
            )
        mesh_state = to_mesh_state(grid, color_array_name)
        showScalarBar = (
            self.show_scalar_bar
            and color_array_name is not None
            and color_data_range is not None
        )
        mapper = {
            "scalarMode": 3,
            "scalarVisibility": True,
            "interpolateScalarsBeforeMapping": True,
        }
        if color_array_name:
            mapper["colorByArrayName"] = color_array_name
        return View(
            GeometryRepresentation(
                [
                    Mesh(state=mesh_state),
                ],
                showScalarBar=showScalarBar,
                scalarBarTitle=(color_array_name if showScalarBar else None),
                mapper=mapper,
                actor={},
                colorMapPreset=(color_map if showScalarBar else None),
                colorDataRange=(color_data_range if showScalarBar else None),
                property={
                    "edgeVisibility": False,
                    "pointSize": self.point_size,
                    "lineWidth": self.line_width,
                    "opacity": self.opacity,
                    "representation": self.representation_type,
                },
            ),
            id=VTK_VIEW_ID.get_identifier(),
            background=colors.hex2color(self.background_color),
            style={"height": "100vh", "width": "100%", "margin": 0, "padding": 0},
        )
