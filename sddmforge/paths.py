"""Path resolution: bundled theme, working copy, and system targets."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

THEME_NAME = "maia-theme"

# System targets (written by apply.py with privilege)
SYSTEM_THEMES_DIR = Path("/usr/share/sddm/themes")
SYSTEM_THEME_DIR = SYSTEM_THEMES_DIR / THEME_NAME
SDDM_CONF = Path("/etc/sddm.conf")
SDDM_CONF_D = Path("/etc/sddm.conf.d")
DROPIN = SDDM_CONF_D / "10-maia.conf"

WAYLAND_SESSIONS = Path("/usr/share/wayland-sessions")
X11_SESSIONS = Path("/usr/share/xsessions")


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))


def app_data_dir() -> Path:
    return xdg_data_home() / "sddm-forge"


def work_theme_dir() -> Path:
    """Working copy of the theme — where the app writes and the preview reads."""
    return app_data_dir() / "work" / THEME_NAME


def backups_dir() -> Path:
    return app_data_dir() / "backups"


def _candidate_bundled_theme_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        # running from the repo: <repo>/sddmforge/paths.py -> <repo>/theme/maia-theme
        here.parent.parent / "theme" / THEME_NAME,
        # installed: <data>/sddm-forge/theme/maia-theme next to the package
        here.parent.parent / "share" / "sddm-forge" / "theme" / THEME_NAME,
        xdg_data_home() / "sddm-forge" / "bundled-theme" / THEME_NAME,
        Path("/usr/share/sddm-forge/theme") / THEME_NAME,
    ]


def bundled_theme_dir() -> Path:
    for cand in _candidate_bundled_theme_dirs():
        if (cand / "Main.qml").is_file():
            return cand
    raise FileNotFoundError(
        "bundled theme not found (looked in: "
        + ", ".join(str(p) for p in _candidate_bundled_theme_dirs())
        + ")"
    )


def ensure_work_theme() -> Path:
    """Ensure the working copy; seed it from the bundled theme if Main.qml is missing."""
    work = work_theme_dir()
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "Main.qml").is_file():
        src = bundled_theme_dir()
        for item in src.iterdir():
            dest = work / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    return work


def reseed_work_theme() -> Path:
    """Re-copy Main.qml/metadata/assets from the bundle, keeping theme.conf."""
    work = ensure_work_theme()
    src = bundled_theme_dir()
    for item in src.iterdir():
        if item.name == "theme.conf":
            continue
        dest = work / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    return work


def _newer(a: Path, b: Path) -> bool:
    """True if `a` exists and is newer (or `b` does not exist)."""
    if not b.exists():
        return True
    return a.stat().st_mtime > b.stat().st_mtime + 1


def sync_work_theme() -> Path:
    """Keep the working copy's QML in sync with the bundle, without touching
    theme.conf. Called on every start: Main.qml is app code, not the user's —
    it must never fall behind."""
    work = ensure_work_theme()
    src = bundled_theme_dir()
    for name in ("Main.qml", "metadata.desktop"):
        s = src / name
        if s.is_file() and _newer(s, work / name):
            shutil.copy2(s, work / name)
    # layout.json is user state: only seed it if missing
    seed_layout = src / "layout.json"
    if seed_layout.is_file() and not (work / "layout.json").is_file():
        shutil.copy2(seed_layout, work / "layout.json")
    src_assets = src / "assets"
    if src_assets.is_dir():
        dst_assets = work / "assets"
        dst_assets.mkdir(exist_ok=True)
        for a in src_assets.iterdir():
            if a.is_file() and _newer(a, dst_assets / a.name):
                shutil.copy2(a, dst_assets / a.name)
    return work
