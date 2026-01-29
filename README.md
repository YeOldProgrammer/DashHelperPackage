# Dash Helper

Summarizes Dash callback arguments into a single object.
Provides easy access to inputs, states, and trigger information.

## Installation

```bash
pip install dash-helper
```

## Usage

```python
import dash
from dash import html, Input, Output, State
from src.dash_helper.dash_helper import dash_helper

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Button("Click Me", id="btn"),
    html.Div(id="output")
])


@dash_helper(app, Output("output", "children"), Input("btn", "n_clicks"))
def update_output(dh):
    if dh.triggered_id == "btn":
        dh.set("output", "children", "Button Clicked!")
    else:
        dh.set("output", "children", "Initial State")


if __name__ == "__main__":
    app.run_server(debug=True)
```
