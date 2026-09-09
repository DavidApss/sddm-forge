"""Página Temas: escolher o tema ativo e (re)instalar o tema embutido."""

from __future__ import annotations

from .. import paths
from ..widgets import group, page


def _installed_themes() -> list[str]:
    out = set()
    if paths.SYSTEM_THEMES_DIR.is_dir():
        for entry in paths.SYSTEM_THEMES_DIR.iterdir():
            if (entry / "metadata.desktop").is_file() or (entry / "Main.qml").is_file():
                out.add(entry.name)
    out.add(paths.THEME_NAME)  # ainda não instalado, mas é o nosso alvo
    return sorted(out)


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Temas", "preferences-desktop-theme-symbolic")

    themes = _installed_themes()
    cur = cfg.get_sddm("Theme", "Current") or paths.THEME_NAME
    if cur not in themes:
        themes.append(cur)
    g = group("Tema ativo", "Gravado como [Theme] Current no drop-in")
    g.add(
        b.combo(
            "Current",
            themes,
            cur,
            lambda v: cfg.set_sddm("Theme", "Current", v),
        )
    )
    p.add(g)

    g2 = group(
        "Tema Maia (embutido)",
        "O sddm-forge instala/atualiza o tema 'maia-theme' a partir da sua "
        "cópia embutida ao clicar em Aplicar.",
    )
    from gi.repository import Adw, Gtk

    row = Adw.ActionRow(
        title="Restaurar Main.qml/assets do embutido",
        subtitle="Descarta modificações locais no QML (mantém suas opções)",
    )
    btn = Gtk.Button(label="Restaurar", valign=Gtk.Align.CENTER)
    btn.connect("clicked", lambda _b: window.reseed_theme())
    row.add_suffix(btn)
    g2.add(row)
    p.add(g2)

    g3 = group("Serviço")
    g3.add(
        b.switch(
            "Habilitar SDDM no boot",
            "systemctl enable sddm.service ao aplicar",
            window.enable_service,
            lambda v: window.set_enable_service(v),
        )
    )
    p.add(g3)

    return p
