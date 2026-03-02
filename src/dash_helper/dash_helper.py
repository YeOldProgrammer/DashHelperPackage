"""
Dash helper logic.   Simplify the passing of data into and out of a dash callback.
  - instead of passing input and output based on a strict ordering, can specify key/values of only the fields you care about
  - better ability to catch incorrect callback values to speed up development
  - enhanced logging / debugging
  - easier to detach callback to allow for standalone testing
"""
import dash
import inspect
import dash
from pathlib import Path
from dash.dependencies import ComponentIdType
import json
import logging
import copy
from datetime import datetime, timezone
from urllib.parse import parse_qs

from sqlalchemy import values
from tabulate import tabulate

IO_INPUT = 'input'
IO_STATE = 'state'
IO_OUTPUT = 'output'

LOG_EVENT_NO_CHANGE = 'no_change'
LOG_EVENT_ERROR = 'error'
LOG_EVENT_COMPLETED = 'completed'

LOGGER = logging.getLogger('dash_helper')

DEBUG_INDENT = '  '
DEBUG_CALL_BACK = 'admin:update_user_table'
TRIGGER_FIELDS = {
    'index': 'trigger_idx',
    'role': 'trigger_role',
    'type': 'trigger_id',
}

class DashHelper:
    """
    Summarizes Dash callback arguments into a single object.
    Provides easy access to inputs, states, and trigger information.
    """

    def __init__(self, inputs_def, states_def, outputs_def, args=None,
                 dash_app_name=None, callback_name=None, debug=False, location_id=None,
                 log_on_exit=False, cb_file=None, cb_path=None, cb_line=None, standalone_mode = False,
                 trigger_id=None, trigger_prop=None, skip_no_callback=False, prevent_initial_update=False,
                 func=None):
        self.standalone_mode = standalone_mode
        if self.standalone_mode is False:
            self.ctx = dash.callback_context
        else:
            self.ctx = None

        self.cb_file = cb_file
        self.cb_path = cb_path
        self.cb_line = cb_line
        self.debug = debug
        self.log_on_exit = log_on_exit
        self.location_id = location_id
        self.location_pathname = None
        self.location_hash = None
        for trigger_field in TRIGGER_FIELDS.values():
            setattr(self, trigger_field, None)
        self.trigger_prop = None
        self.trigger_val = None
        self.trigger_count = 0
        self.trigger_id_str = None
        self.trigger_dict = {}
        self.process_trigger()
        self.location_params = {}
        self.dash_app_name = dash_app_name
        self.callback_name = callback_name
        self.skip_no_callback = skip_no_callback
        self.prevent_initial_update = prevent_initial_update

        if args is None:
            args = []

        self._name = format_callback_name(self.dash_app_name, self.callback_name)
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

        co_obj = CallOrigin('__init__', depth=1)

        # Map inputs
        count = 0
        for definition, val in zip(inputs_def, input_vals):
            count += 1
            try:
                key, prop = self._make_key(definition, co_obj=co_obj)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                LOGGER.error(error_msg, exc_info=True)
                raise ValueError(error_msg)

            if key not in self._inputs:
                self._inputs[key] = {}
            self._inputs[key][prop] = val

        # Map states
        count = 0
        for definition, val in zip(states_def, state_vals):
            count += 1
            try:
                key, prop = self._make_key(definition, co_obj=co_obj)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                LOGGER.error(error_msg, exc_info=True)
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
                    LOGGER.error(error_msg)
                    raise ValueError(error_msg)

        # Map outputs
        count = 0
        for definition in outputs_def:
            count += 1
            try:
                key, prop = self._make_key(definition, co_obj=co_obj)
            except Exception as e:
                error_msg = f"[{self._name}] Unable to process input ({count}) '{definition.component_id}': {e}"
                LOGGER.error(error_msg, exc_info=True)
                raise ValueError(error_msg)
            self._output_order.append({'key': key, 'prop': prop})
            if key not in self._outputs:
                self._outputs[key] = {}
            self._outputs[key][prop] = dash.no_update

        if location_id:
            self._find_location()

    def _make_key(self, definition, property_id=None, helper=None, co_obj=None):
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

        control_property = None
        if isinstance(definition, (dash.Input, dash.State, dash.Output)):
            control_id = definition.component_id
            control_property = definition.component_property
        elif isinstance(definition, dict):
            control_id = definition
        elif isinstance(definition, str):
            if ':' in definition:
                definition_list = definition.split(':')
                if len(definition_list) != 2:
                    error_msg = f"[{self._name}] Key '{definition}' should only have 2 tokens (op={co_obj})"
                    LOGGER.error(error_msg)
                    raise ValueError(error_msg)
                control_id, control_property = definition_list
            else:
                control_id = definition
        else:
            error_msg = f"[{self._name}] Key '{definition}' is not a Input, Output, State object or dict or str (op={co_obj})"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        if property_id is not None:
            control_property = property_id

        if isinstance(control_id, dict):
            if 'type' not in control_id:
                error_msg = f"[{self._name}] Unable to find 'type' in key dict '{control_id}' (op={co_obj})"
                LOGGER.error(error_msg)
                raise ValueError(error_msg)

            control_id = control_id['type']

        elif not isinstance(control_id, str):
            error_msg = f"[{self._name}] Key is not 'str' or 'dict' '{control_id}' (op={co_obj})"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        if control_property is None and isinstance(helper, (list, str)):
            if control_id not in mapping_dict:
                mapping_dict_keys = list(mapping_dict.keys())
                error_msg = f"[{self._name}] Key '{control_id}' does not exist in callbacks {helper} ({self.cb_file}:{self.cb_line}) section(s) ({mapping_dict_keys}) (op={co_obj})"
                LOGGER.error(error_msg)
                raise ValueError(error_msg)
            if len(mapping_dict[control_id]) != 1:
                error_msg = f"[{self._name}] Key '{control_id}' has multiple property_ids - check each '{co_obj}' op for '{control_id}' to make sure it has a property assigned to it"
                LOGGER.error(error_msg)
                raise ValueError(error_msg)
            control_property = list(mapping_dict[control_id].keys())[0]

        if not isinstance(control_property, (str, bool, int, float)):
            if control_id not in mapping_dict:
                control_property_list = list(mapping_dict[control_id].keys())
                error_msg = f"[{self._name}] Key '{control_id}' property is not a str ({control_property}) valid {control_property_list} (op={co_obj})"
                LOGGER.error(error_msg)
                raise ValueError(error_msg)
            else:
                prop_type = type(control_property)
                prop_name = prop_type.__class__
                error_msg = f"[{self._name}] Key '{control_id}' property is not a str ({control_property}) type={prop_type} (op={co_obj})"
                LOGGER.error(error_msg)
                raise ValueError(error_msg)

        return control_id, control_property

    def _find_location(self):
        location_component = self._states.get(self.location_id, {})
        self.location_pathname = location_component.get('pathname', None)
        self.location_hash = location_component.get('hash', None)
        params = location_component.get('search', None)
        if params:
            # Remove leading '?' if present
            if params.startswith('?'):
                params = params[1:]

            # Parse query string into a dictionary
            parsed_params = parse_qs(params)

            # parse_qs returns values as lists, flatten them if single value
            self.location_params = {k: v[0] if len(v) == 1 else v for k, v in parsed_params.items()}
        else:
            self.location_params = {}

    def process_trigger(self):
        self.trigger_prop = None
        self.trigger_val = None
        self.trigger_count = 0
        self.trigger_dict = {}
        self.raw_trigger_id = None
        self.trigger_id_str = None
        first_trigger_fields = {}
        for field in TRIGGER_FIELDS.keys():
            first_trigger_fields[field] = None

        if self.ctx is None:
            return

        try:
            if not self.ctx.triggered:
                return
        except LookupError:
            return

        self.raw_trigger_id = self.ctx.triggered
        if isinstance(self.ctx.triggered, list) is False:
            raise ValueError("Unexpected trigger")

        if len(self.ctx.triggered) == 0:
            return None

        self.trigger_count = len(self.ctx.triggered)

        for idx, trigger in enumerate(self.ctx.triggered):
            if isinstance(trigger, dict) is False:
                raise ValueError("Unexpected trigger")

            this_trigger_fields = {}
            for field in TRIGGER_FIELDS.keys():
                this_trigger_fields[field] = None

            prop_data = trigger.get('prop_id')
            if prop_data is None:
                raise ValueError("Unexpected trigger - missing prop_id")
            if '}.' in prop_data:
                trigger_tok = prop_data.split('}.')
            elif '.' in prop_data:
                trigger_tok = prop_data.split('.')
            else:
                raise ValueError("Unexpected trigger - missing tokens")

            token_count = len(trigger_tok)
            if token_count != 2:
                raise ValueError(f"Unexpected trigger prop_id, expected 2 tokens, found {token_count}")

            trigger_prop = trigger_tok[1]
            trigger_val = trigger.get('value')
            if '{' in trigger_tok[0]:
                try:
                    trigger_dict = json.loads(trigger_tok[0] + '}')
                except json.JSONDecodeError:
                    raise ValueError("Unexpected trigger prop_id")

                trigger_id = trigger_dict.get('index')
                for field in trigger_dict.keys():
                    if field not in TRIGGER_FIELDS:
                        LOGGER.warning(f"Unexpected trigger field '{field}' found for trigger '{trigger_id}'")

                for field in TRIGGER_FIELDS.keys():
                    this_trigger_fields[field] = trigger_dict.get(field, None)
            else:
                trigger_id = trigger_tok[0]
                this_trigger_fields['index'] = trigger_tok[0]

            trigger_prop = trigger_tok[1]
            trigger_val = trigger.get('value')

            if idx == 0:
                for field, field_name in TRIGGER_FIELDS.items():
                    setattr(self, field_name, this_trigger_fields.get(field))
                self.trigger_prop = trigger_prop
                self.trigger_val = trigger_val

            temp_dict = {}
            for field, value in this_trigger_fields.items():
                temp_dict[field] = value
            temp_dict['prop'] = trigger_prop
            temp_dict['value'] = trigger_val
            self.trigger_dict[trigger_id] = copy.copy(temp_dict)

        if self.trigger_idx:
            self.trigger_id_str = f"{self.trigger_id}:{self.trigger_idx}"
        else:
            self.trigger_id_str = self.trigger_id

    @property
    def return_value(self):
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
                LOGGER.error(error_msg)
                raise ValueError(error_msg)
            if prop not in self._outputs[key]:
                error_msg = f"[{self._name}] Key '{key}' Prop: '{prop}' does not exist in outputs"
                LOGGER.error(error_msg)
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
            output = f"[{self._name}] Callback Info: trigger component='{self.trigger_id_str}' cnt={self.trigger_count} prop='{self.trigger_prop}' cb=[{self.cb_file}:{self.cb_line}]\n"

            output += f"URL Location:\n"
            if self.location_id:
                output += f"    pathname='{self.location_pathname}'\n"
                output += f"    params={self.location_params}\n"
                output += f"    hash='{self.location_hash}'\n"
            else:
                output += f"    None\n"

            input_count = len(self._inputs)
            states_count = len(self._states)
            output_count = len(self._outputs)
            output += f"Inputs ({input_count}):\n"
            for input_id, input_val in self._inputs.items():
                if 1 == 0:
                    output += f"    * {input_id}: {input_val}\n"
                else:
                    output += f"      {input_id}: {input_val}\n"

            output += f"States ({states_count}):\n"
            for state_id, state_val in self._states.items():
                if 1 == 0:
                    output += f"    * {state_id}: {state_val}\n"
                else:
                    output += f"      {state_id}: {state_val}\n"

            output += f"Outputs ({output_count}):\n"
            for output_id, output_val in self._outputs.items():
                if output_val == dash.no_update:
                    output += f"      {output_id}: None\n"
                elif isinstance(output_val, dict) and 'children' in output_val and output_val['children'] == dash.no_update and len(output_val) == 1:
                    output += f"      {output_id}: {{'children': None}}\n"
                else:
                    output += f"      {output_id}: {output_val}\n"

        except Exception as e:
            output = '<<<error generating output>>>'
            LOGGER.error("Failed to generate output: %s", e, exc_info=True)

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
            LOGGER.error(output, exc_info=True)
            raise ValueError(output)

    def _find_callback_io_dict(self, io_list, component_id, property_id=None, allow_invalid=False, co_obj=None):
        key, prop = self._make_key(definition=component_id, property_id=property_id, helper=io_list, co_obj=co_obj)

        if property_id is not None:
            prop = property_id

        for io_type in io_list:
            io_dict = self._get_io_dict(io_type)

            if key in io_dict:
                if prop is None:
                    if len(self._outputs[key]) != 1:
                        caller_frame = inspect.stack()[1]
                        error_msg = f"[{self._name}] io='{io_type}' component_id='{component_id}' has multiple properties defined ({co_obj})"
                        LOGGER.error(error_msg)
                        raise ValueError(error_msg)

                    prop = list(io_dict[key].keys())[0]

                if prop in io_dict[key]:
                    return io_dict, key, prop

        # If we are here we didn't find a match on the key/prop
        if not allow_invalid:
            error_msg = f"[{self._name}] io='{io_list}' component_id='{component_id}' property_id='{property_id}'"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        return None, component_id, property_id

    def get(self, component_id, property_id=None, default=None, allow_invalid=False):
        """Retrieve a callback's Input or State value by its ID."""
        # We force allow_invalid=True to support returning the default value if not found
        co_obj = CallOrigin('get', depth=2)
        io_dict, key, prop = self._find_callback_io_dict([IO_INPUT, IO_STATE], component_id,
                                                         property_id=property_id, allow_invalid=allow_invalid,
                                                         co_obj=co_obj)

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

    def set(self, component_id, value=dash.no_update, property_id=None, co_obj=None):
        """ Set the value of a callbacks output by its ID """
        if co_obj is None:
            co_obj = CallOrigin('set', depth=2)
        io_dict, key, prop = self._find_callback_io_dict([IO_OUTPUT], component_id, property_id=property_id,
                                                         co_obj=co_obj)
        io_dict[key][prop] = value

    def set_dict(self, output_dict):
        """ Take a dictionary of output and associated values and call set method on each one """
        co_obj = CallOrigin('set', depth=2)
        for component_id, value in output_dict.items():
            key, prop = self._make_key(component_id, helper=IO_OUTPUT, co_obj=co_obj)
            self.set(component_id=component_id, property_id=prop, value=value, co_obj=co_obj)

    def set_list(self, output_list):
        """ Take a dictionary of output and associated values and call set method on each one """
        output_list_len = len(output_list)
        output_callback_len = len(self._output_order)
        if output_list_len != output_callback_len:
            error_msg = f"[{self._name}] set_list passed {output_list_len}, expecting {output_callback_len} {self._output_order}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        for idx in range(output_list_len):
            key = self._output_order[idx]['key']
            prop = self._output_order[idx]['prop']
            value = output_list[idx]
            self.set(component_id=key, property_id=prop, value=value)

    def callback_log_done(self, log_level, event, message, show_debug=False, exc_info=False):
        if not self.debug and event != LOG_EVENT_NO_CHANGE:
            return
        if exc_info is False:
            exc_info = event == LOG_EVENT_ERROR
        dur = (datetime.now(tz=timezone.utc) - self._start).total_seconds()
        if self.trigger_id and self.trigger_prop:
            output = f"[{self._name}:{self.trigger_id}:{self.trigger_prop}] {message} (time={dur}s)"
        elif self.trigger_id:
            output = f"[{self._name}:{self.trigger_id}] {message} (time={dur}s)"
        else:
            output = f"[{self._name}:None] {message} (time={dur}s)"

        if show_debug is True:
            output += f"\n{self.debug_str}"
        LOGGER.log(log_level, output, exc_info=exc_info)

    def __str__(self):
        return self.debug_str

def get_comp_id_index1(component):
    if isinstance(component, dict):
        component_id = component['type']
        component_index = component['index']
    elif isinstance(component, (dash.Input, dash.State, dash.Output)):
        if hasattr(component, 'component_id'):
            component_id = component.component_id.get('type')
            component_index = component.component_id.get('index')
        else:
            raise ValueError("missing property")
    else:
        component_id = component
        component_index = None

    return component_id, component_index

def get_comp_id_index2(component):
    if hasattr(component, 'component_type'):
        component_type = component.component_type
    else:
        component_type = 'not-defined'

    if isinstance(component, dict):
        component_id = component['type']
        component_index = component.get('index')
    elif isinstance(component, (dash.Input, dash.State, dash.Output)):
        if isinstance(component, dict):
            component_id = component.component_id['type']
            component_index = component.component_id.get('index')
        elif isinstance(component.component_id, str):
            component_id = component.component_id
            component_index = None
        elif isinstance(component.component_id, dict):
            component_id = component.component_id.get('type')
            component_index = component.component_id.get('index')
        else:
            raise ValueError("uncaught component structure")
    else:
        component_id = component
        component_index = None

    return component_id, component_index, component_type


def get_dash_helper_arg(my_kwargs, field_name, default_value=None):
    """
    Return dash helper arg
    :param my_kwargs: dict of args
    :param field_name: field to look for
    :param default_value: default value to return if not found
    :return: found value
    """
    if field_name not in my_kwargs:
        return default_value

    arg_val = my_kwargs.get(field_name, default_value)
    del my_kwargs[field_name]
    return arg_val

def format_callback_name(dash_app_name, callback_name):
    if dash_app_name and callback_name:
        cb_name_str = f'{dash_app_name}:{callback_name}'
    elif callback_name:
        cb_name_str = f':{callback_name}'
    elif dash_app_name:
        cb_name_str = f'{dash_app_name}:'
    else:
        cb_name_str = 'invalid'
    return cb_name_str

def find_control_ids(app, dash_app_name, callback_name, layout=None):
    # Find location component ID
    control_ids = {}
    app_layout = None

    if layout is None:
        if not hasattr(app, 'layout'):
            raise ValueError('app does not have a layout populated')
        app_layout = app.layout

    elif callable(layout):
        app_layout = layout()

    else:
        app_layout = layout

    if not app_layout:
        raise ValueError('app has a layout but it is is not populated')

    try:
        def find_controls(dash_app_name, callback_name, component, my_control_ids):
            if hasattr(component, 'id'):
                my_type = type(component).__name__
                if component.id in my_control_ids:
                    callback_name_str = format_callback_name(dash_app_name, callback_name)
                    raise ValueError(f"Control ID '{component.id}' has been used multiple times in the layout "
                                     f"'{callback_name_str}' first='{my_control_ids[component.id]}' second='{my_type}'")
                else:
                    my_control_ids[component.id] = my_type

            if hasattr(component, 'children'):
                children = component.children
                if isinstance(children, list):
                    for child in children:
                        res = find_controls(dash_app_name, callback_name, child, my_control_ids)
                        if res: return res
                elif children:
                    return find_controls(dash_app_name, callback_name, children, my_control_ids)
            return None

        find_controls(dash_app_name, callback_name, app_layout, control_ids)

    except Exception as e:
        raise e

    return control_ids

def validate_component(app, dash_app_name, callback_name, component_group, component_list, layout_component_ids):
    strict = not app.config['suppress_callback_exceptions']
    for callback_component in component_list:
        component_id, component_index = get_comp_id_index1(callback_component.component_id)
        component_type = layout_component_ids.get(component_id, None)
        if not component_type:
            if strict:
                cb_name_str = format_callback_name(dash_app_name, callback_name)
                raise ValueError(f"App '{app.title}' callback '{cb_name_str}' has {component_group} id '{component_id}' that is not found on layout.   Valid component ids are {list(layout_component_ids.keys())}")

def add_location_info(flat_args, location_id, defined_states, args):
    location_pathname_found = False
    location_search_found = False
    location_hash_found = False

    for component in flat_args:
        if isinstance(component, dash.Input) or isinstance(component, dash.State):
            if component.component_id == location_id:
                if component.component_property.lower() == 'pathname':
                    location_pathname_found = True
                elif component.component_property.lower() == 'search':
                    location_search_found = True
                elif component.component_property.lower() == 'hash':
                    location_hash_found = True

        else:
            continue

    if not location_pathname_found:
        new_state = dash.State(location_id, 'pathname')
        defined_states.append(new_state)
        args.append(new_state)

    if not location_search_found:
        new_state = dash.State(location_id, 'search')
        defined_states.append(new_state)
        args.append(new_state)

    if not location_hash_found:
        new_state = dash.State(location_id, 'hash')
        defined_states.append(new_state)
        args.append(new_state)

def dash_helper(*args, **kwargs):
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

    caller_frame = inspect.stack()[2]
    cb_path = caller_frame.filename
    cb_file = Path(cb_path).stem
    cb_line = caller_frame.lineno

    my_kwargs = kwargs.copy()
    app = get_dash_helper_arg(my_kwargs, 'app')
    if app is None:
        app = dash.get_app()
        if app is None:
            error = "No dash application found initialized"
            LOGGER.error(error)
            raise LookupError(error)

    dash_app_name = get_dash_helper_arg(my_kwargs, 'dash_app_name')
    if not dash_app_name:
        dash_app_name = cb_file

    callback_name = get_dash_helper_arg(my_kwargs, 'callback_name')
    skip_no_callback = get_dash_helper_arg(my_kwargs, 'skip_no_callback', False)
    debug = get_dash_helper_arg(my_kwargs, 'debug')
    log_on_exit = get_dash_helper_arg(my_kwargs, 'log_on_exit')
    layout = get_dash_helper_arg(my_kwargs, 'layout')
    prevent_initial_update = kwargs.get('prevent_initial_update', False)

    layout_component_ids = find_control_ids(app, dash_app_name, callback_name, layout=layout)
    if len(layout_component_ids) == 0:
        error = f"Dash App '{app.title}' layout has no components found"
        LOGGER.error(error)
        raise ValueError(error)

    # Extract definitions
    defined_inputs = [x for x in flat_args if isinstance(x, dash.Input)]
    defined_states = [x for x in flat_args if isinstance(x, dash.State)]
    defined_outputs = [x for x in flat_args if isinstance(x, dash.Output)]

    # Make sure input / state / output IDs all exist in layout - note not existing is fine
    validate_component(app, dash_app_name, callback_name, 'input', defined_inputs, layout_component_ids)
    validate_component(app, dash_app_name, callback_name, 'state', defined_states, layout_component_ids)
    validate_component(app, dash_app_name, callback_name, 'output', defined_outputs, layout_component_ids)
    location_id = next((k for k, v in layout_component_ids.items() if v == 'Location'), None)

    # If a location is present in the layout, but not present in an input or states, add it in as a state
    if location_id:
        my_args = list(args)
        add_location_info(flat_args, location_id, defined_states, my_args)
        args = tuple(my_args)

    def display_dash_helper_init():
        cb_name_str = format_callback_name(dash_app_name, callback_name)
        debug_str = f"Registered Callback [{cb_name_str}] at {cb_file}:{cb_line} (prevent_initial_update={prevent_initial_update})\n"
        layout_info = []

        # TODO Remove
        if cb_name_str == DEBUG_CALL_BACK:
            a = 1

        for callback_component, component_type in layout_component_ids.items():
            input_list = []
            state_list = []
            output_list = []
            component_id, component_index = get_comp_id_index1(callback_component)

            for component in defined_inputs:
                if component.component_id == component_id:
                    input_list.append(component.component_property)

            for component in defined_states:
                if component.component_id == component_id:
                    state_list.append(component.component_property)

            for component in defined_outputs:
                if component.component_id == component_id:
                    output_list.append(component.component_property)

            layout_dict = {
                'component_id': component_id,
                'component_type': component_type,
                'component_index': component_index,
                'input': ', '.join(input_list),
                'state': ', '.join(state_list),
                'output': ', '.join(output_list)
            }
            layout_info.append(layout_dict)

        for component in defined_inputs:
            component_id, component_index, component_type = get_comp_id_index2(component)
            if component_id not in layout_component_ids:
                layout_info.append({
                    'component_id': component_id,
                    'component_type': '???',
                    'component_index': component_index,
                    'input': component_type,
                    'state': '',
                    'output': '',
                })

        for component in defined_states:
            component_id, component_index, component_type = get_comp_id_index2(component)
            if component_id not in layout_component_ids:
                layout_info.append({
                    'component_id': component_id,
                    'component_type': '???',
                    'component_index': component_index,
                    'input': '',
                    'state': '',
                    'output': component_type,
                })

        for component in defined_outputs:
            component_id, component_index, component_type = get_comp_id_index2(component)
            if component_id not in layout_component_ids:
                layout_info.append({
                    'component_id': component_id,
                    'component_type': '???',
                    'component_index': component_index,
                    'input': '',
                    'state': '',
                    'output': component_type,
                })

        table_str = tabulate(layout_info, headers='keys', tablefmt='psql')
        table_str = table_str.replace('\n', '\n' + DEBUG_INDENT)
        debug_str += DEBUG_INDENT + table_str + '\n'
        LOGGER.info(debug_str)

        # TODO Remove
        if cb_name_str == DEBUG_CALL_BACK:
            a = 1

    def decorator(func):
        @app.callback(*args, **my_kwargs)
        def wrapper(*cb_args):
            try:
                dh = DashHelper(defined_inputs, defined_states, defined_outputs, cb_args,
                                dash_app_name=dash_app_name,
                                callback_name=callback_name,
                                debug=debug,
                                cb_file=cb_file,
                                cb_path=cb_path,
                                cb_line=cb_line,
                                log_on_exit=log_on_exit,
                                location_id=location_id,
                                skip_no_callback=skip_no_callback,
                                prevent_initial_update=prevent_initial_update,
                                )
            except Exception as e:
                LOGGER.error(f"Error in DashHelper: {e}", exc_info=True)
                return dash.no_update

            # If no change, just return no update
            if dh.raw_trigger_id is None and (dh.skip_no_callback is True or dh.prevent_initial_update is True):
                dh.callback_log_done(logging.DEBUG, LOG_EVENT_NO_CHANGE, "Callback Result: No change",
                                     show_debug=dh.log_on_exit)
                return dash.no_update

            try:
                return_value = func(dh)

                # Use return value from method
                if isinstance(return_value, tuple):
                    dh.set_list(return_value)
                elif return_value and return_value != dash.no_update:
                    dh.set_list([return_value,])

                dh.callback_log_done(logging.INFO, LOG_EVENT_COMPLETED, "Callback Result: Completed",
                                     show_debug=dh.log_on_exit)

                return dh.return_value

            except Exception as e:
                dh.callback_log_done(logging.ERROR, LOG_EVENT_ERROR, f"Callback Result: Failed: {e}",
                                     show_debug=True, exc_info=True)
                return dash.no_update

        return wrapper

    if debug:
        display_dash_helper_init()

    return decorator


def dash_helper_register(*args, **kwargs):
    func = get_dash_helper_arg(kwargs, 'func')
    if func is None:
        raise ValueError("dash_helper_register requires a 'func' argument")

    if kwargs.get('callback_name') is None:
        kwargs['callback_name'] = func.__name__

    # Call the dash_helper decorator logic
    # dash_helper returns a decorator, which we then call with the function
    decorator = dash_helper(*args, **kwargs)
    decorator(func)


class Output():  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        component_id: ComponentIdType,
        component_property: str,
        allow_duplicate: bool = False,
    ):
        self.component_id = component_id
        self.component_property = component_property
        self.allow_duplicate = allow_duplicate

    def to_obj(self):
        return dash.Output(component_id=self.component_id,
                           component_property=self.component_property,
                           allow_duplicate=self.allow_duplicate
                           )


class Input():  # pylint: disable=too-few-public-methods
    """Input of callback: trigger an update when it is updated."""

    def __init__(
        self,
        component_id: ComponentIdType,
        component_property: str,
        allow_optional: bool = False,
        trigger: bool = False,
        value: str = None,
    ):
        self.component_id = component_id
        self.component_property = component_property
        self.allow_optional = allow_optional
        self.trigger = trigger
        self.value = value

    def to_obj(self):
        return dash.Input(component_id=self.component_id,
                          component_property=self.component_property,
                          allow_optional=self.allow_optional
                          )

class State():  # pylint: disable=too-few-public-methods
    """Use the value of a State in a callback but don't trigger updates."""

    def __init__(
        self,
        component_id: ComponentIdType,
        component_property: str,
        allow_optional: bool = False,
        value: str = None,
    ):
        self.component_id = component_id
        self.component_property = component_property
        self.allow_optional = allow_optional
        self.value = value

    def to_obj(self):
        return dash.State(component_id=self.component_id,
                          component_property=self.component_property,
                          allow_optional=self.allow_optional
                          )

class CallOrigin:
    def __init__(self, name=None, depth=1):
        self.name = name
        caller_frame = inspect.stack()[depth]
        self.call_path = caller_frame.filename
        self.call_file = Path(self.call_path).stem
        self.call_line = caller_frame.lineno

    def __repr__(self):
        if self.name:
            output = f'{self.name}:{self.call_file}:{self.call_line}'
        else:
            output = f'{self.call_file}:{self.call_line}'
        return output


class DashHelperGen:
    def __init__(self, *args, **kwargs):
        self.inputs = []
        self.states = []
        self.outputs = []
        self.values = []

        kwargs['standalone_mode'] = True

        for arg in args:
            if isinstance(arg, Input):
                self.inputs.append(arg.to_obj())
                self.values.append(arg.value)
                if arg.trigger is True:
                    if 'trigger_id' in kwargs:
                        raise ValueError(f'Trigger ID already set')
                    if 'trigger_prop' in kwargs:
                        raise ValueError(f'Trigger Property already set')
                    kwargs['trigger_id'] = arg.component_id
                    kwargs['trigger_prop'] = arg.component_property

        for arg in args:
            if isinstance(arg, State):
                self.states.append(arg.to_obj())
                self.values.append(arg.value)

        for arg in args:
            if isinstance(arg, Output):
                self.outputs.append(arg.to_obj())


        self.dh_obj = DashHelper(self.inputs, self.states, self.outputs, self.values, **kwargs)
