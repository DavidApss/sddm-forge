"""System section: everything that goes in the SDDM drop-in, not the theme.

Merges what used to be three tabs (Autologin, SDDM, Users): they are all the
same file — /etc/sddm.conf.d/10-maia.conf — and none of them touch the visuals.
"""

from __future__ import annotations

import pwd
from pathlib import Path

from .. import paths
from ..model import NUMLOCK_VALUES
from ..widgets import group, page

_NUMLOCK_LABELS = ["Leave alone", "On", "Off"]


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


def _login_group(window) -> "object":
    cfg = window.cfg
    b = window.binder
    g = group(
        "Automatic login",
        "Logs in directly without a password. Leave the user empty to disable.",
    )

    users = [""] + _human_users()
    cur_user = cfg.get_sddm("Autologin", "User")
    if cur_user and cur_user not in users:
        users.append(cur_user)
    g.add(b.combo(
        "User", users, cur_user,
        lambda v: cfg.set_sddm("Autologin", "User", v),
        labels=["Disabled"] + users[1:],
    ))

    sessions = [""] + _sessions()
    cur_sess = cfg.get_sddm("Autologin", "Session")
    if cur_sess and cur_sess not in sessions:
        sessions.append(cur_sess)
    g.add(b.combo(
        "Session", sessions, cur_sess,
        lambda v: cfg.set_sddm("Autologin", "Session", v),
        labels=["Default"] + sessions[1:],
    ))

    g.add(b.switch(
        "Log back in after logout", "Relogin",
        (cfg.get_sddm("Autologin", "Relogin") or "false").lower() == "true",
        lambda v: cfg.set_sddm("Autologin", "Relogin", "true" if v else "false"),
    ))
    return g


def _greeter_group(window) -> "object":
    cfg = window.cfg
    b = window.binder
    g = group("Greeter session", "SDDM's own options when drawing the screen")

    g.add(b.combo(
        "Numlock at startup", NUMLOCK_VALUES,
        cfg.get_sddm("General", "Numlock") or "none",
        lambda v: cfg.set_sddm("General", "Numlock", v),
        labels=_NUMLOCK_LABELS,
    ))

    cursors = _cursor_themes()
    cur = cfg.get_sddm("Theme", "CursorTheme")
    cur_opts = ["", *cursors] if cur in ("", *cursors) else ["", cur, *cursors]
    g.add(b.combo(
        "Cursor theme", cur_opts, cur,
        lambda v: cfg.set_sddm("Theme", "CursorTheme", v),
        labels=["Default"] + cur_opts[1:],
    ))
    g.add(b.entry(
        "Greeter font", cfg.get_sddm("Theme", "Font"),
        lambda v: cfg.set_sddm("Theme", "Font", v),
    ))
    g.add(b.switch(
        "HiDPI (Wayland)", "EnableHiDPI",
        (cfg.get_sddm("Wayland", "EnableHiDPI") or "true").lower() == "true",
        lambda v: cfg.set_sddm("Wayland", "EnableHiDPI", "true" if v else "false"),
    ))
    return g


def _users_group(window) -> "object":
    cfg = window.cfg
    b = window.binder
    g = group("Who shows in the list", "Filters for the login screen's user list")

    g.add(b.spin(
        "Minimum UID", 0, 65000, 1,
        int(cfg.get_sddm("Users", "MinimumUid") or 1000),
        lambda v: cfg.set_sddm("Users", "MinimumUid", str(int(v))),
    ))
    g.add(b.spin(
        "Maximum UID", 0, 65000, 1,
        int(cfg.get_sddm("Users", "MaximumUid") or 60000),
        lambda v: cfg.set_sddm("Users", "MaximumUid", str(int(v))),
    ))
    g.add(b.entry(
        "Hidden users", cfg.get_sddm("Users", "HideUsers"),
        lambda v: cfg.set_sddm("Users", "HideUsers", v.strip()),
    ))
    g.add(b.entry(
        "Hidden shells", cfg.get_sddm("Users", "HideShells"),
        lambda v: cfg.set_sddm("Users", "HideShells", v.strip()),
    ))
    return g


def build(window) -> "object":
    p = page("System", "applications-system-symbolic")
    p.add(_login_group(window))
    p.add(_greeter_group(window))
    p.add(_users_group(window))
    p.add(group(
        "Where this is written",
        "/etc/sddm.conf.d/10-maia.conf — a dedicated drop-in; the distro "
        "defaults are left untouched.",
    ))
    return p
