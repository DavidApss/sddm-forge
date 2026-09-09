"""Página Usuários: filtros de quem aparece na lista do SDDM."""

from __future__ import annotations

from ..widgets import group, page


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Usuários", "system-users-symbolic")

    g = group("Faixa de UID", "Só usuários nesta faixa aparecem na tela de login")
    g.add(
        b.spin(
            "UID mínimo",
            0,
            65000,
            1,
            int(cfg.get_sddm("Users", "MinimumUid") or 1000),
            lambda v: cfg.set_sddm("Users", "MinimumUid", str(int(v))),
        )
    )
    g.add(
        b.spin(
            "UID máximo",
            0,
            65000,
            1,
            int(cfg.get_sddm("Users", "MaximumUid") or 60000),
            lambda v: cfg.set_sddm("Users", "MaximumUid", str(int(v))),
        )
    )
    p.add(g)

    g2 = group("Ocultar", "Listas separadas por vírgula")
    g2.add(
        b.entry(
            "Usuários ocultos",
            cfg.get_sddm("Users", "HideUsers"),
            lambda v: cfg.set_sddm("Users", "HideUsers", v.strip()),
        )
    )
    g2.add(
        b.entry(
            "Shells ocultos",
            cfg.get_sddm("Users", "HideShells"),
            lambda v: cfg.set_sddm("Users", "HideShells", v.strip()),
        )
    )
    p.add(g2)

    return p
