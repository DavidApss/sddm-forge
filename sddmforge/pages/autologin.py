"""Página Autologin."""

from __future__ import annotations

import pwd
from pathlib import Path

from .. import paths
from ..widgets import group, page


def _human_users() -> list[str]:
    out = []
    for entry in pwd.getpwall():
        if 1000 <= entry.pw_uid < 60000 and "nologin" not in entry.pw_shell:
            out.append(entry.pw_name)
    return sorted(set(out))


def _sessions() -> list[str]:
    out = []
    for d in (paths.WAYLAND_SESSIONS, paths.X11_SESSIONS):
        if d.is_dir():
            out += [p.name for p in sorted(d.glob("*.desktop"))]
    return out


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Autologin", "system-users-symbolic")

    g = group(
        "Login automático",
        "Entra direto sem pedir senha. Deixe o usuário vazio para desligar.",
    )

    users = [""] + _human_users()
    cur_user = cfg.get_sddm("Autologin", "User")
    if cur_user and cur_user not in users:
        users.append(cur_user)
    g.add(
        b.combo(
            "Usuário",
            users,
            cur_user,
            lambda v: cfg.set_sddm("Autologin", "User", v),
            labels=["(desligado)"] + users[1:],
        )
    )

    sessions = [""] + _sessions()
    cur_sess = cfg.get_sddm("Autologin", "Session")
    if cur_sess and cur_sess not in sessions:
        sessions.append(cur_sess)
    g.add(
        b.combo(
            "Sessão",
            sessions,
            cur_sess,
            lambda v: cfg.set_sddm("Autologin", "Session", v),
            labels=["(padrão)"] + sessions[1:],
        )
    )

    g.add(
        b.switch(
            "Relogin",
            "Voltar a logar automaticamente após logout",
            (cfg.get_sddm("Autologin", "Relogin") or "false").lower() == "true",
            lambda v: cfg.set_sddm("Autologin", "Relogin", "true" if v else "false"),
        )
    )
    p.add(g)

    return p
