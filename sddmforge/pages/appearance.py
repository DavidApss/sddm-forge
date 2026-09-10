"""Appearance section: background, blur, colors, font."""

from __future__ import annotations

import math
import shutil
from pathlib import Path

from .. import paths
from ..model import (
    BACKGROUND_MODES,
    BUTTON_STYLES,
    CONTROL_ICONS,
    CONTROL_STYLES,
    INPUT_STYLES,
)
from ..widgets import group, page

_MODE_LABELS = ["Video", "Image", "Solid color"]
_INPUT_LABELS = {"underline": "Underline", "box": "Box",
                 "pill": "Pill", "segmented": "Segmented"}
_BTN_LABELS = {"outline": "Outline", "fill": "Filled", "pill": "Pill"}
_CTL_LABELS = {"text": "Text", "outline": "Outline", "pill": "Pill"}
_ICON_LABELS = {"off": "No icon", "only": "Icon only", "label": "Icon + label"}


# --- schematics for the "Widget style" chips ---------------------------
def _c(area):
    rgba = area.get_color()
    return (rgba.red, rgba.green, rgba.blue, rgba.alpha)


def _rrect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _draw_input(area, cr, w, h, key, _sel):
    cr.set_source_rgba(*_c(area))
    m = 6.0
    x, y, ww, hh = m, m + 2, w - 2 * m, h - 2 * m - 4
    cr.set_line_width(1.5)
    if key == "underline":
        cr.move_to(x + 2, y + 4)
        cr.line_to(x + ww * 0.55, y + 4)
        cr.stroke()
        cr.set_line_width(2.0)
        cr.move_to(x, y + hh)
        cr.line_to(x + ww, y + hh)
        cr.stroke()
    elif key == "box":
        _rrect(cr, x, y, ww, hh, 3)
        cr.stroke()
    elif key == "pill":
        _rrect(cr, x, y, ww, hh, hh / 2)
        cr.stroke()
    elif key == "segmented":
        gap, n = 3.0, 4
        seg = (ww - (n - 1) * gap) / n
        for i in range(n):
            _rrect(cr, x + i * (seg + gap), y + hh * 0.15, seg, hh * 0.7, 2)
            cr.stroke()


def _draw_button(area, cr, w, h, key, _sel):
    cr.set_source_rgba(*_c(area))
    m = 7.0
    x, y, ww, hh = m, h * 0.28, w - 2 * m, h * 0.44
    cr.set_line_width(1.5)
    _rrect(cr, x, y, ww, hh, hh / 2 if key == "pill" else 3)
    cr.stroke() if key == "outline" else cr.fill()


def _draw_control(area, cr, w, h, key, _sel):
    cr.set_source_rgba(*_c(area))
    m, gap, n = 5.0, 4.0, 3
    seg = (w - 2 * m - (n - 1) * gap) / n
    y, hh = h * 0.30, h * 0.40
    cr.set_line_width(1.3)
    for i in range(n):
        x = m + i * (seg + gap)
        if key == "text":
            cr.arc(x + seg / 2, y + hh / 2, 1.6, 0, 2 * math.pi)
            cr.fill()
        elif key == "outline":
            _rrect(cr, x, y, seg, hh, 2.5)
            cr.stroke()
        elif key == "pill":
            _rrect(cr, x, y, seg, hh, hh / 2)
            cr.fill()


def _import_asset(src_path: str) -> str:
    """Copy the chosen file into the working copy's assets/."""
    src = Path(src_path)
    assets = paths.work_theme_dir() / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    dest = assets / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return f"assets/{src.name}"


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Appearance", "applications-graphics-symbolic")

    g_bg = group("Background")
    g_bg.add(
        b.combo(
            "Mode",
            BACKGROUND_MODES,
            cfg.theme["backgroundMode"],
            lambda v: cfg.set_theme("backgroundMode", v),
            labels=_MODE_LABELS,
        )
    )
    g_bg.add(
        b.image(
            "Background image",
            cfg.theme["background"],
            lambda v: cfg.set_theme("background", v),
            paths.work_theme_dir() / "assets",
            window,
        )
    )
    g_bg.add(
        b.file(
            "Background video",
            cfg.theme["backgroundVideo"],
            lambda v: cfg.set_theme("backgroundVideo", _import_asset(v)),
            window,
        )
    )
    g_bg.add(b.color("Solid color / base", cfg.theme["bgColor"],
                     lambda v: cfg.set_theme("bgColor", v)))
    g_bg.add(b.spin("Blur (image)", 0, 128, 1, cfg.theme["blurRadius"],
                    lambda v: cfg.set_theme("blurRadius", v)))
    g_bg.add(b.spin("Blur (video)", 0, 64, 1, cfg.theme["videoBlurRadius"],
                    lambda v: cfg.set_theme("videoBlurRadius", v)))
    g_bg.add(b.spin("Dimming", 0.0, 1.0, 0.05, cfg.theme["dimOpacity"],
                    lambda v: cfg.set_theme("dimOpacity", v), digits=2))
    p.add(g_bg)

    g_col = group("Colors")
    for key, title in [
        ("accentColor", "Accent"),
        ("accentColorDim", "Accent (dim)"),
        ("textColor", "Text"),
        ("subTextColor", "Secondary text"),
        ("errorColor", "Error"),
    ]:
        g_col.add(b.color(title, cfg.theme[key],
                          lambda v, k=key: cfg.set_theme(k, v)))
    p.add(g_col)

    g_font = group("Typography")
    g_font.add(b.entry("Font", cfg.theme["fontFamily"],
                       lambda v: cfg.set_theme("fontFamily", v)))
    g_font.add(b.spin("Clock size", 16, 200, 1, cfg.theme["clockFontSize"],
                      lambda v: cfg.set_theme("clockFontSize", v)))
    g_font.add(b.spin("Date size", 8, 64, 1, cfg.theme["dateFontSize"],
                      lambda v: cfg.set_theme("dateFontSize", v)))
    g_font.add(b.spin("Name size", 10, 80, 1, cfg.theme["nameFontSize"],
                      lambda v: cfg.set_theme("nameFontSize", v)))
    p.add(g_font)

    g_st = group("Widget style")
    g_st.add(b.chips("Password field", INPUT_STYLES, cfg.theme["inputStyle"],
                     lambda v: cfg.set_theme("inputStyle", v), _draw_input,
                     labels=[_INPUT_LABELS[x] for x in INPUT_STYLES]))
    g_st.add(b.chips("Login button", BUTTON_STYLES, cfg.theme["buttonStyle"],
                     lambda v: cfg.set_theme("buttonStyle", v), _draw_button,
                     labels=[_BTN_LABELS[x] for x in BUTTON_STYLES]))
    g_st.add(b.chips("Session / power buttons", CONTROL_STYLES,
                     cfg.theme["controlStyle"],
                     lambda v: cfg.set_theme("controlStyle", v), _draw_control,
                     labels=[_CTL_LABELS[x] for x in CONTROL_STYLES]))
    g_st.add(b.toggles("Icons on power buttons", CONTROL_ICONS,
                       cfg.theme["controlIcons"],
                       lambda v: cfg.set_theme("controlIcons", v),
                       labels=[_ICON_LABELS[x] for x in CONTROL_ICONS]))
    p.add(g_st)

    return p
