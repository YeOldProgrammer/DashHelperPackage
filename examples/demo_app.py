import dash
from dash import html, Input, Output
import sys
import os
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('demo_app')

# Add the project root/src to sys.path to allow importing dash_helper
# This is necessary if dash_helper is not installed in the environment
# We go up one level from 'examples' to project root, then into 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dash_helper import dash_helper

app = dash.Dash(__name__)

DASH_CONTROL_BUTTON1_INPUT_ID = 'btn1'
DASH_CONTROL_BUTTON1_INPUT_PROP = 'n_clicks'
DASH_CONTROL_BUTTON2_INPUT_ID = 'btn2'
DASH_CONTROL_BUTTON2_INPUT_PROP = 'n_clicks'
DASH_CONTROL_BUTTON3_INPUT_ID = 'btn3'
DASH_CONTROL_BUTTON3_INPUT_PROP = 'n_clicks'
DASH_CONTROL_DIV_OUTPUT_ID = 'output'
DASH_CONTROL_DIV_OUTPUT_PROP = 'children'

app.layout = html.Div([
    html.H1("Dash Helper Demo"),
    html.Button("Click Me", id=DASH_CONTROL_BUTTON1_INPUT_ID),
    html.Button("Click Me", id=DASH_CONTROL_BUTTON2_INPUT_ID),
    html.Button("Click Me", id=DASH_CONTROL_BUTTON3_INPUT_ID),
    html.Div(id=DASH_CONTROL_DIV_OUTPUT_ID, style={"marginTop": "20px"})
])

@dash_helper(app,
             Output(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
             Input(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON1_INPUT_PROP),
             Input(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON2_INPUT_PROP),
             prevent_initial_call=True,
             callback_name="btn1_btn2"
             )
def update_output_btn1_btn2(dh):
    # dh is the DashHelper object
    if dh.triggered_id == DASH_CONTROL_BUTTON1_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON1_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button1 Clicked! Count: {n_clicks}")
    elif dh.triggered_id == DASH_CONTROL_BUTTON2_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON2_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button2 Clicked! Count: {n_clicks}")
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    logger.info(dh)

@dash_helper(app,
             Output(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
             Input(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON3_INPUT_PROP),
             prevent_initial_call=True,
             callback_name="btn3"
             )
def update_output_btn3(dh):
    # dh is the DashHelper object

    if dh.triggered_id == DASH_CONTROL_BUTTON3_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON3_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button3 Clicked! Count: {n_clicks}")
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    logger.info(dh)

if __name__ == "__main__":
    app.run(debug=True)
