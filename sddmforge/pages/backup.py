"""Página Backup: lista e restaura snapshots feitos a cada Aplicar."""

from __future__ import annotations

import json

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import group, page


def _backups() -> list["object"]:
    root = paths.backups_dir()
    if not root.is_dir():
        return []
    return sorted((d for d in root.iterdir() if d.is_dir()), reverse=True)


def build(window) -> "object":
    p = page("Backup", "document-revert-symbolic")

    g = group(
        "Snapshots",
        "Criados automaticamente antes de cada Aplicar, em "
        f"{paths.backups_dir()}",
    )

    entries = _backups()
    if not entries:
        g.add(Adw.ActionRow(title="Nenhum backup ainda"))
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
            parts.append("tema")
        if manifest.get("dropin"):
            parts.append("drop-in")
        subtitle = ", ".join(parts) if parts else "estado vazio (sem tema/drop-in)"

        row = Adw.ActionRow(title=d.name, subtitle=subtitle)
        btn = Gtk.Button(label="Restaurar", valign=Gtk.Align.CENTER)
        btn.add_css_class("destructive-action")
        btn.connect("clicked", lambda _b, path=str(d): window.restore_backup(path))
        row.add_suffix(btn)
        g.add(row)

    p.add(g)
    return p
