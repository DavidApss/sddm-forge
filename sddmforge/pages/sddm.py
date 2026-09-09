"""Página SDDM: opções do próprio SDDM (drop-in /etc/sddm.conf.d/10-maia.conf)."""

from __future__ import annotations

from pathlib import Path

from ..model import NUMLOCK_VALUES
from ..widgets import group, page

_NUMLOCK_LABELS = ["Não mexer", "Ligado", "Desligado"]


def _cursor_themes() -> list[str]:
    roots = [
        Path("/usr/share/icons"),
        Path.home() / ".local/share/icons",
        Path.home() / ".icons",
    ]
    found = set()
    for root in roots:
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if (entry / "cursors").is_dir() or (entry / "cursor.theme").is_file():
                found.add(entry.name)
    return sorted(found)


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("SDDM", "preferences-system-symbolic")

    g = group("Sessão do greeter")
    g.add(
        b.combo(
            "Numlock ao iniciar",
            NUMLOCK_VALUES,
            cfg.get_sddm("General", "Numlock") or "none",
            lambda v: cfg.set_sddm("General", "Numlock", v),
            labels=_NUMLOCK_LABELS,
        )
    )

    cursors = _cursor_themes()
    cur = cfg.get_sddm("Theme", "CursorTheme")
    cur_opts = ["", *cursors] if cur in ("", *cursors) else ["", cur, *cursors]
    cur_labels = ["(padrão)"] + cur_opts[1:]
    g.add(
        b.combo(
            "Tema de cursor",
            cur_opts,
            cur,
            lambda v: cfg.set_sddm("Theme", "CursorTheme", v),
            labels=cur_labels,
        )
    )
    g.add(
        b.entry(
            "Fonte do greeter",
            cfg.get_sddm("Theme", "Font"),
            lambda v: cfg.set_sddm("Theme", "Font", v),
        )
    )
    g.add(
        b.switch(
            "HiDPI (Wayland)",
            "EnableHiDPI",
            (cfg.get_sddm("Wayland", "EnableHiDPI") or "true").lower() == "true",
            lambda v: cfg.set_sddm("Wayland", "EnableHiDPI", "true" if v else "false"),
        )
    )
    p.add(g)

    g2 = group(
        "Onde isto é gravado",
        "/etc/sddm.conf.d/10-maia.conf — um drop-in próprio; os defaults da "
        "distro não são tocados.",
    )
    p.add(g2)

    return p
