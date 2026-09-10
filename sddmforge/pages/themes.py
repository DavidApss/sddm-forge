"""Themes section: active theme, (re)installing the bundled theme, service, backups."""

from __future__ import annotations

import json

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import group, page


def _installed_themes() -> list[str]:
    out = set()
    if paths.SYSTEM_THEMES_DIR.is_dir():
        for entry in paths.SYSTEM_THEMES_DIR.iterdir():
            if (entry / "metadata.desktop").is_file() or (entry / "Main.qml").is_file():
                out.add(entry.name)
    out.add(paths.THEME_NAME)  # not installed yet, but it's our target
    return sorted(out)


def _backups() -> list["object"]:
    root = paths.backups_dir()
    if not root.is_dir():
        return []
    return sorted((d for d in root.iterdir() if d.is_dir()), reverse=True)


def _backup_group(window) -> "object":
    g = group(
        "Backups",
        "A snapshot is created automatically before every Apply, in "
        f"{paths.backups_dir()}",
    )

    entries = _backups()
    if not entries:
        row = Adw.ActionRow(title="No backups yet")
        row.set_subtitle("The first Apply creates the initial snapshot")
        g.add(row)
        return g

    for d in entries:
        manifest = {}
        mf = d / "manifest.json"
        if mf.is_file():
            try:
                manifest = json.loads(mf.read_text())
            except json.JSONDecodeError:
                pass
        parts = []
        if manifest.get("theme"):
            parts.append("theme")
        if manifest.get("dropin"):
            parts.append("drop-in")
        subtitle = ", ".join(parts) if parts else "empty state (no theme/drop-in)"

        row = Adw.ActionRow(title=d.name, subtitle=subtitle)
        btn = Gtk.Button(label="Restore", valign=Gtk.Align.CENTER)
        btn.add_css_class("destructive-action")
        btn.connect("clicked", lambda _b, path=str(d): window.restore_backup(path))
        row.add_suffix(btn)
        row.set_activatable_widget(btn)
        g.add(row)
    return g


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Themes", "preferences-desktop-appearance-symbolic")

    themes = _installed_themes()
    cur = cfg.get_sddm("Theme", "Current") or paths.THEME_NAME
    if cur not in themes:
        themes.append(cur)
    g = group("Active theme", "Written as [Theme] Current in the drop-in")
    g.add(b.combo("Current", themes, cur,
                  lambda v: cfg.set_sddm("Theme", "Current", v)))
    p.add(g)

    g2 = group(
        "Maia theme (bundled)",
        "sddm-forge installs/updates 'maia-theme' from the bundled copy on "
        "every Apply.",
    )
    row = Adw.ActionRow(
        title="Restore Main.qml and assets from bundle",
        subtitle="Discards local QML edits (keeps your settings)",
    )
    btn = Gtk.Button(label="Restore", valign=Gtk.Align.CENTER)
    btn.connect("clicked", lambda _b: window.reseed_theme())
    row.add_suffix(btn)
    row.set_activatable_widget(btn)
    g2.add(row)
    p.add(g2)

    g3 = group("Service")
    g3.add(b.switch(
        "Enable SDDM at boot",
        "systemctl enable sddm.service on apply",
        window.enable_service,
        lambda v: window.set_enable_service(v),
    ))
    p.add(g3)

    p.add(_backup_group(window))
    return p
