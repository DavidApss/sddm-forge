"""Schema and default login-screen layout (component tree).

layout.json / theme.conf[General].layoutJson
============================================
{
  "version": 1,
  "root": [ <panel>, <panel>, ... ]      // painted in this order
}

Panel (type = "panel")
----------------------
  id           str      unique identifier (generated)
  name         str      label shown in the GUI
  type         "panel"
  orientation  "column" | "row"            // stack vertically or horizontally
  position     "top-left" | "top-center" | "top-right"
             | "center"
             | "bottom-left" | "bottom-center" | "bottom-right"
             | {"x": <n|"n%">, "y": <n|"n%">}   // panel's top-left corner
  width        "auto" | "fill" | "<n>%" | "<n>"     // n = px
  height       "auto" | "fill" | "<n>%" | "<n>"
  align        "start" | "center" | "end"      // cross-axis alignment of children
  gap          int      space between children (px)
  padding      int      inner padding (px)
  blur         0..100   blur of the background behind the panel
  dim          0..100   darkening over the panel
  bg           ""|"#rrggbb"|"#aarrggbb"      panel background color
  radius       int      corner radius (px)
  children     [ <panel> | <leaf> ]

Leaf
----
  id     str
  type   one of:
    clock date usernameRow userHandle password
    loginButton sessionButton rebootButton powerButton errorMessage
    text spacer
  props by type:
    usernameRow : carousel (bool, ‹ › arrows)
    text        : text (str), size (int)
    spacer      : size (int)

Absolute positions and sizes accept "%" (relative to the screen) or a plain
number (px).
"""

from __future__ import annotations

import copy
import secrets

_PANEL_KEYS = {
    "name": "",
    "orientation": "column",
    "position": "top-left",
    "width": "auto",
    "height": "auto",
    "align": "start",     # cross axis (of the children)
    "justify": "start",   # main axis (content block within the panel)
    "gap": 0,
    "paddingX": 0,
    "paddingY": 0,
    "blur": 0,
    "dim": 0,          # darken (black)
    "tint": "",        # translucent color wash — ""|"#aarrggbb"|"#rrggbb"
    "noise": 0,        # grain (glass/acrylic effect) 0..100
    "bg": "",          # background color (same as tint, kept for compat)
    "border": "",      # edge line — ""|"#aarrggbb"
    "borderWidth": 1,
    "radius": 0,
}

# leaves and their extra props (with default)
LEAF_PROPS: dict[str, dict[str, object]] = {
    "clock": {},
    "date": {},
    "usernameRow": {"carousel": True},
    "userHandle": {},
    "avatar": {"size": 76},
    "password": {},
    "passwordToggle": {"text": "Show password"},
    "loginButton": {},
    "sessionButton": {},
    "sessionName": {},
    "rebootButton": {},
    "powerButton": {},
    "suspendButton": {},
    "errorMessage": {},
    "text": {"text": "Text", "size": 16},
    "separator": {"size": 40},
    "spacer": {"size": 20},
}
LEAF_TYPES = list(LEAF_PROPS)

LEAF_LABELS = {
    "clock": "Clock (time)",
    "date": "Date / weekday",
    "usernameRow": "Username",
    "userHandle": "@username",
    "avatar": "User avatar",
    "password": "Password field",
    "passwordToggle": "Show password (checkbox)",
    "loginButton": "Login button",
    "sessionButton": "Session picker",
    "sessionName": "Session name (text)",
    "rebootButton": "Restart button",
    "powerButton": "Shut down button",
    "suspendButton": "Suspend button",
    "errorMessage": "Error message",
    "text": "Free text",
    "separator": "Separator (line)",
    "spacer": "Spacer",
}

PANEL_POSITIONS = [
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right",
]
ORIENTATIONS = ["column", "row"]
ALIGNMENTS = ["start", "center", "end"]


def new_id() -> str:
    return "n" + secrets.token_hex(4)


def make_leaf(type_: str) -> dict:
    node = {"id": new_id(), "type": type_}
    node.update(copy.deepcopy(LEAF_PROPS.get(type_, {})))
    return node


def make_panel(name: str = "Panel", **over) -> dict:
    node = {"id": new_id(), "type": "panel"}
    node.update(copy.deepcopy(_PANEL_KEYS))
    node["name"] = name
    node.update(over)
    node.setdefault("children", [])
    return node


def _seed() -> dict:
    controls = make_panel(
        "Session / power", orientation="row", position="top-left",
        align="center", gap=26,
    )
    controls["children"] = [
        make_leaf("sessionButton"), make_leaf("rebootButton"),
        make_leaf("powerButton"),
    ]
    clock = make_panel(
        "Clock", orientation="column", position="top-right", gap=4,
    )
    clock["children"] = [make_leaf("date"), make_leaf("clock")]

    login = make_panel(
        "Login", orientation="column", position="bottom-left", gap=14,
    )
    login["children"] = [
        make_leaf("usernameRow"), make_leaf("userHandle"),
        make_leaf("password"), make_leaf("loginButton"),
        make_leaf("errorMessage"),
    ]
    return {"version": 1, "root": [controls, clock, login]}


def default_layout() -> dict:
    return _seed()


def normalize_panel(node: dict) -> dict:
    if node.get("type") != "panel":
        # leaf — keep overrides (accent/size/bold) not in the spec
        out = dict(node)
        out["id"] = node.get("id") or new_id()
        out["type"] = node.get("type", "text")
        for key, dflt in LEAF_PROPS.get(out["type"], {}).items():
            out.setdefault(key, dflt)
        return out
    out = {"id": node.get("id") or new_id(), "type": "panel"}
    for key, dflt in _PANEL_KEYS.items():
        out[key] = node.get(key, dflt)
    # migration: single 'padding' -> paddingX / paddingY
    if "padding" in node:
        out["paddingX"] = node.get("paddingX", node["padding"])
        out["paddingY"] = node.get("paddingY", node["padding"])
    out["children"] = [normalize_panel(c) for c in node.get("children", [])]
    return out


def normalize_layout(tree: dict) -> dict:
    return {
        "version": tree.get("version", 1),
        "root": [normalize_panel(p) for p in tree.get("root", [])],
    }
