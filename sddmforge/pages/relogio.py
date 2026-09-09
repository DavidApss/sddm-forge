"""Página Relógio: formato da hora e da data."""

from __future__ import annotations

from ..widgets import group, page

_CLOCK_FORMATS = ["hh:mm", "HH:mm", "hh:mm AP", "hh:mm:ss"]
_DATE_FORMATS = [
    "dddd, d 'de' MMMM",
    "ddd, dd/MM",
    "dd/MM/yyyy",
    "d MMMM yyyy",
    "dddd",
]
_LOCALES = ["pt_BR", "en_US", "es_ES", "de_DE", "fr_FR", "ja_JP"]


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Relógio", "preferences-system-time-symbolic")

    g = group("Hora")
    g.add(b.combo("Formato", _CLOCK_FORMATS, cfg.theme["clockFormat"],
                  lambda v: cfg.set_theme("clockFormat", v)))
    p.add(g)

    g2 = group("Data", "Adicione/remova o elemento “Data” num painel na aba Layout")
    fmt = cfg.theme["dateFormat"]
    opts = _DATE_FORMATS if fmt in _DATE_FORMATS else [fmt, *_DATE_FORMATS]
    g2.add(b.combo("Formato", opts, fmt,
                   lambda v: cfg.set_theme("dateFormat", v)))
    loc = cfg.theme["dateLocale"]
    locs = _LOCALES if loc in _LOCALES else [loc, *_LOCALES]
    g2.add(b.combo("Locale", locs, loc,
                   lambda v: cfg.set_theme("dateLocale", v)))
    p.add(g2)

    return p
