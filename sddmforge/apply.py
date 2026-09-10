"""Applies the configuration to the system. RUNS AS ROOT (via pkexec).

Usage:  pkexec python3 -m sddmforge.apply <spec.json>

spec.json:
{
  "work_theme_dir": "/home/user/.local/share/sddm-forge/theme/maia-theme",
  "dropin_text": "....",
  "enable_service": false,
  "restore_from": null            // or the path to a backup folder
}
"""

from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SYSTEM_THEMES_DIR = Path("/usr/share/sddm/themes")
THEME_NAME = "maia-theme"
SYSTEM_THEME_DIR = SYSTEM_THEMES_DIR / THEME_NAME
SDDM_CONF_D = Path("/etc/sddm.conf.d")
DROPIN = SDDM_CONF_D / "10-maia.conf"


def _invoking_user() -> pwd.struct_passwd:
    for var in ("PKEXEC_UID", "SUDO_UID"):
        if os.environ.get(var):
            return pwd.getpwuid(int(os.environ[var]))
    name = os.environ.get("SUDO_USER") or os.environ.get("USER")
    if name and name != "root":
        return pwd.getpwnam(name)
    raise SystemExit("could not determine the user that invoked pkexec")


def _chown_r(path: Path, uid: int, gid: int) -> None:
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            try:
                os.chown(Path(root) / name, uid, gid)
            except OSError:
                pass


def _backup(user: pwd.struct_passwd) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(user.pw_dir) / ".local/share/sddm-forge/backups" / stamp
    dest.mkdir(parents=True, exist_ok=True)

    manifest = {"theme": False, "dropin": False}
    if SYSTEM_THEME_DIR.is_dir():
        shutil.copytree(SYSTEM_THEME_DIR, dest / THEME_NAME)
        manifest["theme"] = True
    if DROPIN.is_file():
        shutil.copy2(DROPIN, dest / DROPIN.name)
        manifest["dropin"] = True
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # the whole backups tree belongs to the user
    _chown_r(Path(user.pw_dir) / ".local/share/sddm-forge", user.pw_uid, user.pw_gid)
    return dest


def _install_theme(src: Path) -> None:
    if not (src / "Main.qml").is_file():
        raise SystemExit(f"invalid source theme: {src}")
    SYSTEM_THEMES_DIR.mkdir(parents=True, exist_ok=True)
    if SYSTEM_THEME_DIR.exists():
        shutil.rmtree(SYSTEM_THEME_DIR)
    shutil.copytree(
        src, SYSTEM_THEME_DIR,
        ignore=shutil.ignore_patterns(".preview-*", "*.tmp", "__pycache__"),
    )
    _chown_r(SYSTEM_THEME_DIR, 0, 0)
    os.chmod(SYSTEM_THEME_DIR, 0o755)


def _write_dropin(text: str) -> None:
    SDDM_CONF_D.mkdir(parents=True, exist_ok=True)
    DROPIN.write_text(text, encoding="utf-8")
    os.chmod(DROPIN, 0o644)


def _restore(backup_dir: Path) -> None:
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {
        "theme": (backup_dir / THEME_NAME).is_dir(),
        "dropin": (backup_dir / DROPIN.name).is_file(),
    }

    if manifest.get("theme"):
        _install_theme(backup_dir / THEME_NAME)
    elif SYSTEM_THEME_DIR.exists():
        shutil.rmtree(SYSTEM_THEME_DIR)

    if manifest.get("dropin"):
        _write_dropin((backup_dir / DROPIN.name).read_text(encoding="utf-8"))
    elif DROPIN.exists():
        DROPIN.unlink()


def _enable_service() -> None:
    subprocess.run(["systemctl", "enable", "sddm.service"], check=False)


def main(argv: list[str]) -> int:
    if os.geteuid() != 0:
        print("apply.py must run as root (use pkexec).", file=sys.stderr)
        return 1
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    user = _invoking_user()
    _backup(user)

    restore_from = spec.get("restore_from")
    if restore_from:
        _restore(Path(restore_from))
        print("restored from", restore_from)
        return 0

    work = Path(spec["work_theme_dir"])
    _install_theme(work)
    _write_dropin(spec["dropin_text"])
    if spec.get("enable_service"):
        _enable_service()
    print("applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
