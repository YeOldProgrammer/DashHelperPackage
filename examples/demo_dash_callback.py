"""
Demo calling a dash callback from dash app
"""
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

from dash_helper import dash_helper_register
from demo_dash_logic import DASH_CONTROL_BUTTON1_INPUT_ID, \
    DASH_CONTROL_BUTTON2_INPUT_ID, \
    DASH_CONTROL_BUTTON3_INPUT_ID, \
    DASH_CONTROL_BUTTON4_INPUT_ID, \
    DASH_CONTROL_BUTTON_INPUT_PROP, \
    DASH_CONTROL_DIV_OUTPUT_ID1, \
    DASH_CONTROL_DIV_OUTPUT_ID2, \
    DASH_CONTROL_DIV_OUTPUT_PROP, \
    DEBUG_ENABLED, \
    CALLBACK_INFO_ENABLED, \
    update_output_btn1_btn2, \
    update_output_btn3, \
    update_output_fail_btn4

app = dash.Dash(__name__,
                suppress_callback_exceptions=True)

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
    html.Div(id=DASH_CONTROL_DIV_OUTPUT_ID1, style={"marginTop": "20px"}),
])


dash_helper_register(Output(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
                     Input(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
                     Input(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
                     callback_name="btn1_btn2",  # descriptive name for callback
                     prevent_initial_call=True,  # do not run callback when application started
                     debug=DEBUG_ENABLED,  # if dash helper debugging logic should be used
                     func=update_output_btn1_btn2  # callback function that take a dash helper argument
                     )

dash_helper_register(Output(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
                     Input(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
                     callback_name="btn3",  # descriptive name for callback
                     prevent_initial_call=True,  # do not run callback when application started
                     debug=DEBUG_ENABLED,  # if dash helper debugging logic should be used
                     log_on_exit=True,  # log callback information when callback has completed
                     layout=app.layout,  # explicitly provide layout.   useful if layout is dynamically generated
                     func=update_output_btn3  # callback function that take a dash helper argument
                     )

dash_helper_register(Output(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
                     Input(DASH_CONTROL_BUTTON4_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP),
                     callback_name="btn4_fail",  # descriptive name for callback
                     prevent_initial_call=True,  # do not run callback when application started
                     debug=DEBUG_ENABLED,  # if dash helper debugging logic should be used
                     app=app,  # Demonstration that the app can explicitly be passed in
                     func=update_output_fail_btn4  # callback function that take a dash helper argument
                     )

if __name__ == "__main__":
    app.run(debug=True)
