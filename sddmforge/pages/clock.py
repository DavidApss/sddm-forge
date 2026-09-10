"""Clock section: time and date format."""

from __future__ import annotations

from ..widgets import group, page

_CLOCK_FORMATS = ["hh:mm", "HH:mm", "hh:mm AP", "hh:mm:ss"]
_DATE_FORMATS = [
    "dddd, MMMM d",
    "ddd, MM/dd",
    "MM/dd/yyyy",
    "MMMM d, yyyy",
    "dddd",
]
_LOCALES = ["en_US", "en_GB", "pt_BR", "es_ES", "de_DE", "fr_FR", "ja_JP"]


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Clock", "preferences-system-time-symbolic")

    g = group("Time")
    g.add(b.combo("Format", _CLOCK_FORMATS, cfg.theme["clockFormat"],
                  lambda v: cfg.set_theme("clockFormat", v)))
    p.add(g)

    g2 = group("Date", "Add/remove the “Date” element in a panel on the Layout tab")
    fmt = cfg.theme["dateFormat"]
    opts = _DATE_FORMATS if fmt in _DATE_FORMATS else [fmt, *_DATE_FORMATS]
    g2.add(b.combo("Format", opts, fmt,
                   lambda v: cfg.set_theme("dateFormat", v)))
    loc = cfg.theme["dateLocale"]
    locs = _LOCALES if loc in _LOCALES else [loc, *_LOCALES]
    g2.add(b.combo("Locale", locs, loc,
                   lambda v: cfg.set_theme("dateLocale", v)))
    p.add(g2)

    return p
