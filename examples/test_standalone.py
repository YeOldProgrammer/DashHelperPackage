"""
Demo how to test a standalone function
"""

import os
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from dash_helper import DashHelper, Input, State, Output, DashHelperGen
from demo_dash_logic import update_output_btn1_btn2, DASH_CONTROL_DIV_OUTPUT_ID1, \
                            DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON2_INPUT_ID, \
                            DASH_CONTROL_DIV_OUTPUT_PROP, DASH_CONTROL_BUTTON_INPUT_PROP

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)-12s - %(levelname)-7s - %(filename)-14s:%(lineno)3d - %(message)s'
)

logger = logging.getLogger('demo_app')

def test1():
    dh_obj = DashHelperGen(
                 Output(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, allow_duplicate=True),
                 Input(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP, value=1, trigger=True),
                 Input(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP, value=2),
                 callback_name="btn1_btn2",
                 func=update_output_btn1_btn2).dh_obj
    update_output_btn1_btn2(dh_obj)

if __name__ == "__main__":
    test1()
