"""
Callback functions.   This allows the callback to be invoked from the dash callback, or a testing harness to make it
easier to directly test the logic (like in a regression test) 
"""
import logging
DASH_CONTROL_BUTTON1_INPUT_ID = 'btn1'
DASH_CONTROL_BUTTON2_INPUT_ID = 'btn2'
DASH_CONTROL_BUTTON3_INPUT_ID = 'btn3'
DASH_CONTROL_BUTTON4_INPUT_ID = 'btn4'
DASH_CONTROL_BUTTON_INPUT_PROP = 'n_clicks'
DASH_CONTROL_DIV_OUTPUT_ID1 = 'output1'
DASH_CONTROL_DIV_OUTPUT_ID2 = 'output2'
DASH_CONTROL_DIV_OUTPUT_PROP = 'children'
DEBUG_ENABLED = True
CALLBACK_INFO_ENABLED = True

LOGGER = logging.getLogger('demo_dash_logic')

def update_output_btn1_btn2(dh):
    # dh is the DashHelper object
    if dh.triggered_id == DASH_CONTROL_BUTTON1_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON1_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button1 Clicked! Count: {n_clicks}")
    elif dh.triggered_id == DASH_CONTROL_BUTTON2_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON2_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button2 Clicked! Count: {n_clicks}")
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    if CALLBACK_INFO_ENABLED:
        LOGGER.info(dh)


def update_output_btn3(dh):
    # dh is the DashHelper object

    if dh.triggered_id == DASH_CONTROL_BUTTON3_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON3_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        # dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button3 Clicked! Count: {n_clicks}")
        return f"Button3 Clicked! Count: {n_clicks}"
    else:
        # dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")
        return "No clicks yet."


def update_output_fail_btn4(dh):
    # dh is the DashHelper object

    if dh.triggered_id == DASH_CONTROL_BUTTON4_INPUT_ID:
        n_clicks = dh.get(DASH_CONTROL_BUTTON4_INPUT_ID, DASH_CONTROL_BUTTON_INPUT_PROP)
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, f"Button4 Clicked! Count: {n_clicks}")
        value = 4 / 0  # intentional failure
    else:
        dh.set(DASH_CONTROL_DIV_OUTPUT_ID1, DASH_CONTROL_DIV_OUTPUT_PROP, "No clicks yet.")

    if CALLBACK_INFO_ENABLED:
        LOGGER.info(dh)
