"""Event handlers as data attributes instead of inline onclick= and
friends, so the Content-Security-Policy (csp.py) can forbid inline
script. ACTIONS_JS in app.py listens once on the document and calls the
named function.

    Button(..., **on("click", "copyLink", "/post/x", EL))
        -> data-onclick="copyLink" data-args='["/post/x", "$el"]'
        -> copyLink("/post/x", button)

EL stands for the element itself (what `this` was), VALUE for its
current value. Raw-HTML builders use on_attrs(), which returns the same
attributes as an escaped string.
"""
import json
from html import escape

EL = "$el"
VALUE = "$value"


def on(event: str, fn: str, *args) -> dict:
    attrs = {f"data_on{event}": fn}
    if args:
        attrs["data_args"] = json.dumps(list(args))
    return attrs


def on_attrs(event: str, fn: str, *args) -> str:
    out = f'data-on{event}="{escape(fn)}"'
    if args:
        out += f' data-args="{escape(json.dumps(list(args)))}"'
    return out
