import dash
from dash import html, Input, Output, State, dcc
import sys
import os
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)-12s - %(levelname)-7s - %(filename)-14s:%(lineno)3d - %(message)s'
)

logger = logging.getLogger('demo_app')

# Add the project root/src to sys.path to allow importing dash_helper
# This is necessary if dash_helper is not installed in the environment
# We go up one level from 'examples' to project root, then into 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dash_helper import dash_helper

app = dash.Dash(__name__)

DASH_CONTROL_BUTTON1_INPUT_ID = 'btn1'
DASH_CONTROL_BUTTON2_INPUT_ID = 'btn2'
DASH_CONTROL_BUTTON3_INPUT_ID = 'btn3'
DASH_CONTROL_BUTTON4_INPUT_ID = 'btn4'
DASH_CONTROL_BUTTON_INPUT_PROP = 'n_clicks'
DASH_CONTROL_DIV_OUTPUT_ID = 'output'
DASH_CONTROL_DIV_OUTPUT_PROP = 'children'
DEBUG_ENABLED = True
CALLBACK_INFO_ENABLED = True

app.layout = html.Div([
    html.H1("Dash Helper Demo"),
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.Div([
            html.Button("Click Me", id=DASH_CONTROL_BUTTON1_INPUT_ID, style={'margin': '10px'}),
            html.Button("Click Me", id=DASH_CONTROL_BUTTON2_INPUT_ID, style={'margin': '10px'}),
        ], style={'display': 'flex', 'padding': '2px', 'border': '1px solid black'}),
        html.Div([
            html.Button("Click Me", id=DASH_CONTROL_BUTTON3_INPUT_ID, style={'margin': '10px'}),
        ], style={'display': 'flex', 'padding': '2px', 'border': '1px solid black'}),
        html.Div([
            html.Button("Fail Callback", id=DASH_CONTROL_BUTTON4_INPUT_ID, style={'margin': '10px'}),
        ], style={'display': 'flex', 'padding': '2px', 'border': '1px solid black', 'background': '#ff0000'}),
    ], style={'display': 'flex', 'gap': '10px'}),
    html.Div(id=DASH_CONTROL_DIV_OUTPUT_ID, style={"marginTop": "20px"})
])

@dash_helper(app,
             Output(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
             Input(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
             Input(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
             prevent_initial_call=True,
             callback_name="btn1_btn2",
             debug=DEBUG_ENABLED
             )
def update_output_btn1_btn2(dh):
    # dh is the DashHelper object
    if dh.triggered_id == DASH_CONTROL_BUTTON1_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button1 Clicked! Count: {n_clicks}")
    elif dh.triggered_id == DASH_CONTROL_BUTTON2_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button2 Clicked! Count: {n_clicks}")
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    if CALLBACK_INFO_ENABLED:
        logger.info(dh)

@dash_helper(app,
             Output(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
             Input(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
             prevent_initial_call=True,
             callback_name="btn3",
             debug=DEBUG_ENABLED
             )
def update_output_btn3(dh):
    # dh is the DashHelper object

    if dh.triggered_id == DASH_CONTROL_BUTTON3_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button3 Clicked! Count: {n_clicks}")
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    if CALLBACK_INFO_ENABLED:
        logger.info(dh)

@dash_helper(app,
             Output(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
             Input(DASH_CONTROL_BUTTON4_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
             prevent_initial_call=True,
             callback_name="btn4_fail",
             debug=DEBUG_ENABLED
             )
def update_output_fail_btn4(dh):
    # dh is the DashHelper object

    if dh.triggered_id == DASH_CONTROL_BUTTON4_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON4_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button4 Clicked! Count: {n_clicks}")
        value = 4 / 0  # intentional failure
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    if CALLBACK_INFO_ENABLED:
        logger.info(dh)

if __name__ == "__main__":
    app.run(debug=True)
