"""
Court geometry + figure builder for the 3D half-court in Plotly.
"""

# --- Imports
import numpy as np
import plotly.graph_objects as go

# --- Court constants (feet)   matches NBA diagram
COURT_LENGTH_HALF = 47.0
COURT_WIDTH       = 50.0

RIM_HEIGHT        = 10.0
RIM_RADIUS        = 0.75

BACKBOARD_WIDTH   = 6.0
BACKBOARD_HEIGHT  = 3.5
BACKBOARD_X       = 4.0             # backboard plane from baseline
RIM_TO_BACKBOARD  = 1.25            # 15 inches = 1.25 ft
HOOP_X            = BACKBOARD_X + RIM_TO_BACKBOARD   # 5.25 ft
HOOP_Y            = 0.0

THREE_PT_RADIUS   = 23.75           # 23' 9"
THREE_PT_CORNER   = 22.0
PAINT_WIDTH       = 16.0
FT_LINE_X         = 19.0            # 15' from backboard -> 19' from baseline

# --- Helpers
def line3d(x,y,z, **kw):
    return go.Scatter3d(
        x=x, y=y, z=z, mode="lines",
        line=dict(width=kw.pop("width", 3), color=kw.pop("color", "black")),
        hoverinfo="skip", **kw
    )

def circle3d(xc,yc,zc,r,n=256,**kw):
    t=np.linspace(0,2*np.pi,n)
    return line3d(xc+r*np.cos(t), yc+r*np.sin(t), np.full_like(t,zc), **kw)

def rectangle_outline3d(x0,x1,y0,y1,z=0,**kw):
    xs=[x0,x1,x1,x0,x0]; ys=[y0,y0,y1,y1,y0]; zs=[z]*5
    return line3d(xs,ys,zs,**kw)

def filled_floor_surface(opacity=0.55):  # more transparent
    X=np.array([[0,COURT_LENGTH_HALF],[0,COURT_LENGTH_HALF]])
    Y=np.array([[-COURT_WIDTH/2,-COURT_WIDTH/2],[COURT_WIDTH/2,COURT_WIDTH/2]])
    Z=np.zeros_like(X)
    return go.Surface(
        x=X,y=Y,z=Z,
        colorscale=[(0,"#f5e6d3"),(1,"#f5e6d3")],
        showscale=False, opacity=opacity,
        hoverinfo="skip", hovertemplate=None
    )

def backboard_mesh():
    bb = np.array([
        [BACKBOARD_X, -BACKBOARD_WIDTH/2, RIM_HEIGHT + BACKBOARD_HEIGHT/2],
        [BACKBOARD_X,  BACKBOARD_WIDTH/2, RIM_HEIGHT + BACKBOARD_HEIGHT/2],
        [BACKBOARD_X,  BACKBOARD_WIDTH/2, RIM_HEIGHT - BACKBOARD_HEIGHT/2],
        [BACKBOARD_X, -BACKBOARD_WIDTH/2, RIM_HEIGHT - BACKBOARD_HEIGHT/2],
    ])
    return go.Mesh3d(
        x=bb[:,0], y=bb[:,1], z=bb[:,2],
        i=[0,0], j=[1,2], k=[2,3],  # two triangles
        color="white", opacity=0.98, flatshading=True, showscale=False
    ), line3d(
        [bb[0,0],bb[1,0],bb[2,0],bb[3,0],bb[0,0]],
        [bb[0,1],bb[1,1],bb[2,1],bb[3,1],bb[0,1]],
        [bb[0,2],bb[1,2],bb[2,2],bb[3,2],bb[0,2]], width=4
    )

def add_three_point_line(fig, width=4, color="black", z_up=0.02, full_semicircle=False):
    """
    NBA 3PT line: arc centered at the rim (R=23.75') joined to 22' corner lines.
    The arc now correctly meets the straight segments at y=±22'.
    """
    R  = THREE_PT_RADIUS
    yc = THREE_PT_CORNER  # 22'
    theta0 = np.arcsin(yc / R)           # <-- correct meeting angle
    x_meet = HOOP_X + R * np.cos(theta0) # x where arc meets the straight lines

    # Arc
    if full_semicircle:
        th = np.linspace(-np.pi/2, np.pi/2, 901)
    else:
        th = np.linspace(-theta0, theta0, 721)

    x_arc = HOOP_X + R * np.cos(th)
    y_arc = HOOP_Y + R * np.sin(th)
    z_arc = np.full_like(th, z_up)
    fig.add_trace(line3d(x_arc, y_arc, z_arc, width=width, color=color))

    # Corner straight segments (baseline to join point)
    if not full_semicircle:
        fig.add_trace(line3d([0, x_meet], [ yc,  yc], [z_up, z_up], width=width, color=color))
        fig.add_trace(line3d([0, x_meet], [-yc, -yc], [z_up, z_up], width=width, color=color))


# ---- NEW: one function that builds the court and returns a Figure
def build_court_figure(
    floor_opacity=0.55,
    show_full_3pt_semicircle=False,
    camera_eye=(2.4, 2.2, 2.2),
    height=720
) -> go.Figure:
    fig = go.Figure()

    # Floor & boundaries
    fig.add_trace(filled_floor_surface(opacity=floor_opacity))
    fig.add_trace(rectangle_outline3d(0, COURT_LENGTH_HALF, -COURT_WIDTH/2, COURT_WIDTH/2, width=6))
    fig.add_trace(rectangle_outline3d(0, FT_LINE_X, -PAINT_WIDTH/2, PAINT_WIDTH/2, width=4))

    # Free-throw (top) & restricted arcs
    theta = np.linspace(-np.pi/2, np.pi/2, 240)
    fig.add_trace(line3d(FT_LINE_X + 6*np.cos(theta), 6*np.sin(theta), np.zeros_like(theta), width=4))
    fig.add_trace(line3d(HOOP_X + 4*np.cos(theta),   4*np.sin(theta), np.zeros_like(theta), width=4))

    # 3PT line (arc + corners)
    add_three_point_line(fig, width=4, z_up=0.02, full_semicircle=show_full_3pt_semicircle)

    # Rim + backboard
    fig.add_trace(circle3d(HOOP_X, HOOP_Y, RIM_HEIGHT, RIM_RADIUS, n=256, color="#111", width=8))
    bb_fill, bb_edge = backboard_mesh()
    fig.add_trace(bb_fill); fig.add_trace(bb_edge)

    # Layout / camera
    fig.update_layout(
        showlegend=False,
        scene=dict(
            xaxis=dict(title="x (ft)", range=[0, COURT_LENGTH_HALF], showgrid=False, zeroline=False, backgroundcolor="white"),
            yaxis=dict(title="y (ft)", range=[-COURT_WIDTH/2, COURT_WIDTH/2], showgrid=False, zeroline=False, backgroundcolor="white"),
            zaxis=dict(title="z (ft)", range=[0, 26], showgrid=False, zeroline=False, backgroundcolor="white"),
            camera=dict(eye=dict(x=camera_eye[0], y=camera_eye[1], z=camera_eye[2]), up=dict(x=0, y=0, z=1)),
            aspectmode="manual",
            aspectratio=dict(x=1.0, y=1.05, z=0.9),
        ),
        margin=dict(l=0, r=0, t=35, b=0),
        height=height,
    )
    return fig

__all__ = [
    "COURT_LENGTH_HALF", "COURT_WIDTH", "RIM_HEIGHT", "RIM_RADIUS",
    "BACKBOARD_WIDTH", "BACKBOARD_HEIGHT", "BACKBOARD_X", "RIM_TO_BACKBOARD",
    "HOOP_X", "HOOP_Y", "THREE_PT_RADIUS", "THREE_PT_CORNER",
    "PAINT_WIDTH", "FT_LINE_X",
    "line3d", "circle3d", "rectangle_outline3d", "filled_floor_surface",
    "backboard_mesh", "add_three_point_line", "build_court_figure", "make_court_figure"
]
