import dash
import inspect
from dash import Input, State, Output, callback_context
import json
import logging
from datetime import datetime, timezone

IO_INPUT = 'input'
IO_STATE = 'state'
IO_OUTPUT = 'output'

LOG_EVENT_NO_CHANGE = 'no_change'
LOG_EVENT_ERROR = 'error'
LOG_EVENT_COMPLETED = 'completed'

logger = logging.getLogger('dash_helper')


class DashHelper:
    """
    Summarizes Dash callback arguments into a single object.
    Provides easy access to inputs, states, and trigger information.
    """

    def __init__(self, inputs_def, states_def, outputs_def, args, callback_name=None, debug=False):
        self.ctx = callback_context
        self.debug = debug
        if isinstance(callback_name, str) and callback_name != '':
            self._name = callback_name
        else:
            self._name = 'default'
        self._inputs = {}
        self._states = {}
        self._outputs = {}
        self._output_order = []
        self._start = datetime.now(tz=timezone.utc)

        # Dash passes arguments as a flattened list: [...inputs, ...states]
        # We map these values back to their definitions based on the order they were defined.
        num_inputs = len(inputs_def)
        input_vals = args[:num_inputs]
        state_vals = args[num_inputs:]

        # Map inputs
        count = 0
        for definition, val in zip(inputs_def, input_vals):
            count += 1
            try:
                key, prop = self._make_key(definition)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if key not in self._inputs:
                self._inputs[key] = {}
            self._inputs[key][prop] = val

        # Map states
        count = 0
        for definition, val in zip(states_def, state_vals):
            count += 1
            try:
                key, prop = self._make_key(definition)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            if key not in self._states:
                self._states[key] = {}
            self._states[key][prop] = val

        # Make sure there are no duplicate input & state
        for key in self._inputs:
            if key not in self._states:
                continue

            for prop in self._inputs[key]:
                if prop in self._states[key]:
                    error_msg = f"[{self._name}] input and state both have key='{key}' and property='{prop}'"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        # Map outputs
        count = 0
        for definition in outputs_def:
            count += 1
            try:
                key, prop = self._make_key(definition)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            self._output_order.append({'key': key, 'prop': prop})
            if key not in self._outputs:
                self._outputs[key] = {}
            self._outputs[key][prop] = dash.no_update

    def _make_key(self, definition, property_id=None, helper=None):
        """Convert component_id to a hashable key (string or JSON for dicts)."""
        mapping = {IO_OUTPUT: self._outputs, IO_STATE: self._states, IO_INPUT: self._inputs}
        mapping_dict = {}
        if isinstance(helper, str) and helper in mapping:
            mapping_dict = mapping[helper]
        elif isinstance(helper, list):
            for helper_item in helper:
                if helper_item in mapping:
                    for helper_key, helper_value in mapping[helper_item].items():
                        if helper_key not in mapping_dict:
                            mapping_dict[helper_key] = helper_value

        cp = None
        if isinstance(definition, (Input, State, Output)):
            cid = definition.component_id
            cp = definition.component_property
        elif isinstance(definition, dict):
            cid = definition
        elif isinstance(definition, str):
            if ':' in definition:
                definition_list = definition.split(':')
                if len(definition_list) != 2:
                    error_msg = f"[{self._name}] Key '{definition}' should only have 2 tokens"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                cid, cp = definition_list
            else:
                cid = definition
        else:
            error_msg = f"[{self._name}] Key '{definition}' is not a Input, Output, State object or dict or str"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if property_id is not None:
            cp = property_id

        if isinstance(cid, dict):
            if 'type' not in cid:
                error_msg = f"[{self._name}] Unable to find 'type' in key dict '{cid}'"
                logger.error(error_msg)
                raise ValueError(error_msg)

            cid = cid['type']

        elif not isinstance(cid, str):
            error_msg = f"[{self._name}] Key is not 'str' or 'dict' '{cid}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if cp is None and isinstance(helper, (list, str)):
            if cid not in mapping_dict:
                error_msg = f"[{self._name}] Key '{cid}' does not exist in '{helper}'"
                logger.error(error_msg)
                raise ValueError(error_msg)
            if len(mapping_dict[cid]) != 1:
                error_msg = f"[{self._name}] Key '{cid}' has multiple property_ids"
                logger.error(error_msg)
                raise ValueError(error_msg)
            cp = list(mapping_dict[cid].keys())[0]

        if not isinstance(cp, str):
            if cid not in mapping_dict:
                error_msg = f"[{self._name}] Key '{cid}' property is not a str ({cp})"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                cp_list = list(mapping_dict[cid].keys())
                error_msg = f"[{self._name}] Key '{cid}' property is not a str ({cp}) valid {cp_list}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        return cid, cp

    @property
    def triggered_id(self):
        """Returns the ID of the component that triggered the callback."""
        if not self.ctx.triggered:
            return None

        # prop_id is formatted as 'component_id.property'
        # We use rsplit to safely separate the ID from the property
        raw_id = self.ctx.triggered[0]['prop_id'].rsplit('.', 1)[0]

        # If ID looks like a JSON dict (Pattern Matching), parse it back to a dict
        if raw_id.startswith('{'):
            try:
                return json.loads(raw_id)
            except json.JSONDecodeError:
                pass
        return raw_id

    @property
    def triggered_prop(self):
        """Returns the property name that triggered the callback (e.g., 'n_clicks', 'value')."""
        if not self.ctx.triggered:
            return None
        return self.ctx.triggered[0]['prop_id'].rsplit('.', 1)[1]

    @property
    def output(self):
        """
        The callback should return a list of values as defined by the callbacks output object.   Map the output
        dictionary to this list.
        :return: list of output values
        """
        output_list = []
        for output_field in self._output_order:
            key = output_field['key']
            prop = output_field['prop']
            if key not in self._outputs:
                error_msg = f"[{self._name}] Key '{key}' does not exist in outputs"
                logger.error(error_msg)
                raise ValueError(error_msg)
            if prop not in self._outputs[key]:
                error_msg = f"[{self._name}] Key '{key}' Prop: '{prop}' does not exist in outputs"
                logger.error(error_msg)
                raise ValueError(error_msg)
            output_list.append(self._outputs[key][prop])
        
        # If there is only one output, return the value directly, not a list
        if len(output_list) == 1:
            return output_list[0]
            
        return output_list

    @property
    def debug_str(self):
        """Returns a string displaying the value of the callback."""

        try:
            output = f"[{self._name}] Callback Info: trigger component='{self.triggered_id}' prop='{self.triggered_prop}'\n"

            input_count = len(self._inputs)
            states_count = len(self._states)
            output_count = len(self._outputs)
            output += f"Inputs({input_count})\n"
            for input_id, input_val in self._inputs.items():
                output += f"    {input_id}: {input_val}\n"

            output += f"States({states_count})\n"
            for state_id, state_val in self._states.items():
                output += f"    {state_id}: {state_val}\n"

            output += f"Outputs({output_count})\n"
            for output_id, output_val in self._outputs.items():
                if output_val == dash.no_update:
                    output += f"    {output_id}: None\n"
                else:
                    output += f"    {output_id}: {output_val}\n"

        except Exception as e:
            output = '<<<error generating output>>>'
            logger.error("Failed to generate output: %s", e, exc_info=True)

        return output

    def _get_io_dict(self, io_type):
        """
        Return IO dictionary for the requested io_type
        :param io_type: type
        :return: list of values from the callback
        """
        if io_type == IO_INPUT:
            return self._inputs
        elif io_type == IO_STATE:
            return self._states
        elif io_type == IO_OUTPUT:
            return self._outputs
        else:
            output = f"Invalid IO Type '{io_type}'"
            logger.error(output, exc_info=True)
            raise ValueError(output)

    def _find_callback_io_dict(self, io_list, component_id, property_id=None, allow_invalid=False):
        key, prop = self._make_key(definition=component_id, property_id=property_id, helper=IO_OUTPUT)

        if property_id is not None:
            prop = property_id

        for io_type in io_list:
            io_dict = self._get_io_dict(io_type)

            if key in io_dict:
                if prop is None:
                    if len(self._outputs[key]) != 1:
                        caller_frame = inspect.stack()[1]
                        error_msg = f"[{self._name}] io='{io_type}' component_id='{component_id}' has multiple properties defined (file: {caller_frame.filename}, line: {caller_frame.lineno})"
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                    prop = list(io_dict[key].keys())[0]

                if prop in io_dict[key]:
                    return io_dict, key, prop

        # If we are here we didn't find a match on the key/prop
        if not allow_invalid:
            error_msg = f"[{self._name}] io='{io_list}' component_id='{component_id}' property_id='{property_id}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return None, component_id, property_id

    def get(self, component_id, property_id=None, default=None, allow_invalid=False):
        """Retrieve a callback's Input or State value by its ID."""
        # We force allow_invalid=True to support returning the default value if not found
        io_dict, key, prop = self._find_callback_io_dict([IO_INPUT, IO_STATE], component_id,
                                                         property_id=property_id, allow_invalid=allow_invalid)

        # If io_dict is None it means no match was returned, return the default value
        if io_dict is None:
            return default

        return io_dict[key][prop]

    def __getitem__(self, item):
        """Dictionary-style access for Inputs and States (e.g., dh['my-id'])."""
        val = self.get(item)
        if val is None and self.get(item, default="CHECK_EXISTENCE") == "CHECK_EXISTENCE":
            # Value is genuinely None, which is fine
            return None

        return val

    def set(self, component_id, property_id=None, value=dash.no_update):
        """ Set the value of a callbacks output by its ID """
        io_dict, key, prop = self._find_callback_io_dict([IO_OUTPUT], component_id, property_id=property_id)
        io_dict[key][prop] = value

    def set_dict(self, output_dict):
        """ Take a dictionary of output and associated values and call set method on each one """
        for component_id, value in output_dict.items():
            key, prop = self._make_key(component_id, helper=IO_OUTPUT)
            self.set(component_id=component_id, property_id=prop, value=value)

    def callback_log_done(self, log_level, event, message, show_debug=False):
        if not self.debug and event != LOG_EVENT_NO_CHANGE:
            return
        exc_info = event == LOG_EVENT_ERROR
        dur = (datetime.now(tz=timezone.utc) - self._start).total_seconds()
        output = f"[{self._name}] {message} (time={dur}s)"
        if show_debug is True:
            output += f"\n{self.debug_str}"
        logger.log(log_level, output, exc_info=exc_info)

    def __str__(self):
        return self.debug_str


def get_dash_helper_arg(my_kwargs, field_name):
    """
    Return dash helper arg
    :param my_kwargs: dict of args
    :param field_name: field to look for
    :return: found value
    """
    if field_name not in my_kwargs:
        return None

    arg_val = my_kwargs[field_name]
    del my_kwargs[field_name]
    return arg_val


def dash_helper(app, *args, **kwargs):
    """
    Decorator that replaces app.callback.
    It wraps the callback function, passing a single DashHelper object
    instead of the list of input/state values.
    """
    # Flatten args to identify Inputs and States in the order Dash receives them
    flat_args = []

    def flatten(items):
        if isinstance(items, (list, tuple)):
            for i in items: flatten(i)
        else:
            flat_args.append(items)

    flatten(args)

    # Extract definitions
    defined_inputs = [x for x in flat_args if isinstance(x, Input)]
    defined_states = [x for x in flat_args if isinstance(x, State)]
    defined_outputs = [x for x in flat_args if isinstance(x, Output)]

    my_kwargs = kwargs.copy()
    callback_name = None

    callback_name = get_dash_helper_arg(my_kwargs, 'callback_name')
    debug = get_dash_helper_arg(my_kwargs, 'debug')

    def decorator(func):
        @app.callback(*args, **my_kwargs)
        def wrapper(*cb_args):
            try:
                dh = DashHelper(defined_inputs, defined_states, defined_outputs, cb_args,
                                callback_name=callback_name, debug=debug)
            except Exception as e:
                logger.error(f"Error in DashHelper: {e}")
                return dash.no_update

            # If no change, just return no update
            if dh.triggered_id is None:
                dh.callback_log_done(logging.DEBUG, LOG_EVENT_NO_CHANGE, "Callback Result: No change")
                return dash.no_update

            try:
                func(dh)
                dh.callback_log_done(logging.INFO, LOG_EVENT_COMPLETED, "Callback Result: Completed")
                return dh.output

            except Exception as e:
                dh.callback_log_done(logging.INFO, LOG_EVENT_ERROR, f"Callback Result: Failed: {e}",
                                     show_debug=True)
                return dash.no_update

        return wrapper

    return decorator
