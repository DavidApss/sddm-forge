"""Offscreen theme renderer (PySide6). Separate process from the GUI.

Usage:
    python3 -m sddmforge.preview_render <work_theme_dir> <out_png> [W] [H]

- Loads the theme's Main.qml with stubs in place of the SDDM objects
  (config, sddm, userModel, sessionModel).
- Watches theme.conf: when it changes, updates `config` (a reactive
  QQmlPropertyMap) and re-writes the PNG.
- A "grab" or "anim on/off" command can arrive on stdin.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")

import shutil  # noqa: E402
import subprocess  # noqa: E402
from configparser import ConfigParser  # noqa: E402
from pathlib import Path  # noqa: E402

from PySide6.QtCore import (  # noqa: E402
    Property,
    QFileSystemWatcher,
    QObject,
    QSocketNotifier,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlPropertyMap  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402


# --- stubs for the objects SDDM injects -----------------------------------
class SddmStub(QObject):
    loginFailed = Signal()
    loginSucceeded = Signal()

    @Slot(str, str, int)
    def login(self, *args):
        pass

    @Slot()
    def reboot(self):
        pass

    @Slot()
    def powerOff(self):
        pass

    @Slot()
    def suspend(self):
        pass

    @Slot()
    def hibernate(self):
        pass


USER_NAME = Qt.UserRole + 1
USER_REAL = Qt.UserRole + 2
SESSION_NAME = Qt.UserRole + 4


class ListStub(QObject):
    """Mimics enough of QAbstractItemModel for Main.qml."""

    def __init__(self, rows: list[dict], last_user: str = "", last_index: int = 0):
        super().__init__()
        self._rows = rows
        self._last_user = last_user
        self._last_index = last_index

    @Property(int, constant=True)
    def count(self):
        return len(self._rows)

    @Property(str, constant=True)
    def lastUser(self):
        return self._last_user

    @Property(int, constant=True)
    def lastIndex(self):
        return self._last_index

    @Slot(int, int, result="QVariant")
    def index(self, row, col):
        return row

    @Slot("QVariant", int, result="QVariant")
    def data(self, idx, role):
        try:
            row = self._rows[int(idx)]
        except (IndexError, ValueError, TypeError):
            return ""
        return row.get(role, "")


def make_user_model() -> ListStub:
    rows = [
        {USER_NAME: "alex", USER_REAL: "Alex"},
        {USER_NAME: "guest", USER_REAL: "Guest"},
    ]
    return ListStub(rows, last_user="alex")


def make_session_model() -> ListStub:
    rows = [{SESSION_NAME: "Plasma (Wayland)"}, {SESSION_NAME: "GNOME"}]
    return ListStub(rows, last_index=0)


# --- app ------------------------------------------------------------------
class Renderer(QObject):
    def __init__(self, theme_dir: Path, out_png: Path, size: tuple[int, int]):
        super().__init__()
        self.theme_dir = theme_dir
        self.conf = theme_dir / "theme.conf"
        self.out_png = out_png
        self.out_tmp = out_png.with_name(out_png.name + ".new")
        self.is_video_fallback = False

        self.config = QQmlPropertyMap(self)
        self._load_conf()

        self.view = QQuickView()
        self.view.setColor(Qt.black)
        self.view.setResizeMode(QQuickView.SizeRootObjectToView)
        self.view.resize(*size)
        # keep refs — setContextProperty doesn't take ownership (else GC drops them)
        self._sddm = SddmStub(self)
        self._user_model = make_user_model()
        self._session_model = make_session_model()
        ctx = self.view.rootContext()
        ctx.setContextProperty("config", self.config)
        ctx.setContextProperty("sddm", self._sddm)
        ctx.setContextProperty("userModel", self._user_model)
        ctx.setContextProperty("sessionModel", self._session_model)
        self.view.setSource(QUrl.fromLocalFile(str(theme_dir / "Main.qml")))
        for err in self.view.errors():
            sys.stderr.write("QML: " + err.toString() + "\n")
        self.view.show()

        self.watcher = QFileSystemWatcher(self)
        self._arm_watch()
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watcher.directoryChanged.connect(lambda _p: self._arm_watch())

        self.anim = QTimer(self)
        self.anim.setInterval(500)
        self.anim.timeout.connect(self.grab)

        QTimer.singleShot(150, self.grab)
        QTimer.singleShot(600, self.grab)
        QTimer.singleShot(1400, self.grab)

    def _arm_watch(self):
        if str(self.conf) not in self.watcher.files() and self.conf.exists():
            self.watcher.addPath(str(self.conf))
        if str(self.theme_dir) not in self.watcher.directories():
            self.watcher.addPath(str(self.theme_dir))

    def _load_conf(self):
        parser = ConfigParser(interpolation=None)
        parser.optionxform = str
        try:
            parser.read(self.conf, encoding="utf-8")
        except Exception:  # noqa: BLE001
            return
        if not parser.has_section("General"):
            return
        values = dict(parser.items("General"))

        # QtMultimedia's video sink doesn't work offscreen: in "video" mode we
        # show a static frame of the video as an image.
        if values.get("backgroundMode") == "video":
            poster = self._video_poster(values.get("backgroundVideo", ""))
            if poster:
                values["backgroundMode"] = "image"
                values["background"] = poster
                # in video mode the theme uses the lighter blur (videoBlurRadius)
                values["blurRadius"] = values.get("videoBlurRadius", "4")
                self.is_video_fallback = True
        else:
            self.is_video_fallback = False

        values["previewMode"] = "1"
        for key, val in values.items():
            self.config.insert(key, val)

    def _video_poster(self, rel_video: str) -> str:
        if shutil.which("ffmpeg") is None or not rel_video:
            return ""
        video = (self.theme_dir / rel_video).resolve()
        if not video.is_file():
            return ""
        poster = self.theme_dir / ".preview-poster.jpg"
        try:
            if not poster.exists() or poster.stat().st_mtime < video.stat().st_mtime:
                subprocess.run(
                    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                     "-i", str(video), "-vframes", "1", "-vf", "scale=1280:-2",
                     str(poster)],
                    check=True, timeout=20,
                )
        except (subprocess.SubprocessError, OSError):
            return ""
        return poster.name if poster.is_file() else ""

    @Slot(str)
    def _on_file_changed(self, _path):
        QTimer.singleShot(60, self._reload)

    def _reload(self):
        self._arm_watch()
        self._load_conf()
        for delay in (80, 400, 1000):
            QTimer.singleShot(delay, self.grab)

    @Slot()
    def grab(self):
        img = self.view.grabWindow()
        if img.isNull():
            return
        # atomic write (tmp + rename), then signal via stdout — the GUI is
        # notified through stdout, not a file watcher, so the rename is fine
        if img.save(str(self.out_tmp), "PNG"):
            os.replace(self.out_tmp, self.out_png)
            sys.stdout.write("frame\n")
            sys.stdout.flush()

    @Slot(str)
    def handle_command(self, line: str):
        line = line.strip()
        if line == "grab":
            self.grab()
        elif line == "anim on":
            self.anim.start()
        elif line == "anim off":
            self.anim.stop()
        elif line == "quit":
            QGuiApplication.quit()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write(__doc__ or "")
        return 2
    theme_dir = Path(argv[1]).expanduser()
    out_png = Path(argv[2]).expanduser()
    w = int(argv[3]) if len(argv) > 3 else 1920
    h = int(argv[4]) if len(argv) > 4 else 1080

    app = QGuiApplication(argv[:1])
    renderer = Renderer(theme_dir, out_png, (w, h))

    notifier = QSocketNotifier(sys.stdin.fileno(), QSocketNotifier.Type.Read)

    def on_stdin(_fd):
        data = sys.stdin.readline()
        if not data:  # EOF: the GUI closed
            app.quit()
            return
        renderer.handle_command(data)

    notifier.activated.connect(on_stdin)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
