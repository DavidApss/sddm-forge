"""Pré-visualização: embutida (render offscreen) e em tela cheia (greeter real)."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from gi.repository import Gdk, Gio, GLib

from . import paths

_GREETERS = ["sddm-greeter-qt6", "sddm-greeter"]

# aresta longa máxima do render offscreen (mantém proporção da tela real)
MAX_EDGE = 1920
FALLBACK_SIZE = (1920, 1080)


def greeter_bin() -> str | None:
    for name in _GREETERS:
        found = shutil.which(name)
        if found:
            return found
    return None


def live_available() -> bool:
    """A prévia embutida precisa do PySide6 (QtQuick)."""
    try:
        return importlib.util.find_spec("PySide6.QtQuick") is not None
    except (ImportError, ValueError):
        return False


class FullscreenPreview:
    """Abre o `sddm-greeter-qt6 --test-mode` (render real, interativo)."""

    def __init__(self) -> None:
        self._proc: Gio.Subprocess | None = None

    def stop(self) -> None:
        if self._proc is not None:
            try:
                self._proc.force_exit()
            except GLib.Error:
                pass
            self._proc = None

    def launch(self) -> None:
        binary = greeter_bin()
        if binary is None:
            raise FileNotFoundError("sddm-greeter-qt6 não encontrado (pacote sddm).")
        self.stop()
        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE
        )
        self._proc = launcher.spawnv(
            [binary, "--test-mode", "--theme", str(paths.work_theme_dir())]
        )
        self._proc.wait_async(None, self._reap, None)

    def _reap(self, proc, result, _data) -> None:
        try:
            proc.wait_finish(result)
        except GLib.Error:
            pass
        if proc is self._proc:
            self._proc = None


class LivePreview:
    """Roda o renderizador offscreen e avisa a GUI a cada frame novo (PNG)."""

    def __init__(
        self, on_frame: Callable[[str], None], parent_window=None
    ) -> None:
        self._on_frame = on_frame
        self._window = parent_window
        self._proc: Gio.Subprocess | None = None
        self._stdin: Gio.OutputStream | None = None
        self._stdout: Gio.DataInputStream | None = None
        # inclui o PID: duas instâncias do app não brigam pelo mesmo arquivo
        import os
        self._png = Path(
            GLib.get_user_runtime_dir() or GLib.get_tmp_dir()
        ) / f"sddm-forge-preview.{os.getpid()}.png"

    @property
    def png_path(self) -> str:
        return str(self._png)

    def is_running(self) -> bool:
        return self._proc is not None

    def _render_script(self) -> Path:
        return (Path(__file__).parent / "preview_render.py").resolve()

    def _render_size(self) -> tuple[int, int]:
        """Resolução da tela real (a do monitor da janela), com proporção
        preservada e aresta longa limitada a MAX_EDGE."""
        w, h = FALLBACK_SIZE
        try:
            display = (
                self._window.get_display() if self._window is not None
                else Gdk.Display.get_default()
            )
            monitor = None
            if self._window is not None and self._window.get_surface() is not None:
                monitor = display.get_monitor_at_surface(self._window.get_surface())
            if monitor is None:
                monitors = display.get_monitors()
                if monitors.get_n_items():
                    monitor = monitors.get_item(0)
            if monitor is not None:
                geo = monitor.get_geometry()
                w, h = geo.width, geo.height
        except Exception:  # noqa: BLE001
            pass
        scale = min(1.0, MAX_EDGE / max(w, h))
        return max(2, round(w * scale)), max(2, round(h * scale))

    def start(self) -> None:
        if self._proc is not None or not live_available():
            return
        paths.ensure_work_theme()
        try:
            self._png.unlink()
        except FileNotFoundError:
            pass

        python = shutil.which("python3") or sys.executable
        rw, rh = self._render_size()
        argv = [
            python, str(self._render_script()),
            str(paths.work_theme_dir()), str(self._png),
            str(rw), str(rh),
        ]
        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
        )
        log = paths.app_data_dir() / "preview.log"
        try:
            paths.app_data_dir().mkdir(parents=True, exist_ok=True)
            launcher.set_stderr_file_path(str(log))
        except (GLib.Error, OSError):
            pass
        try:
            self._proc = launcher.spawnv(argv)
        except GLib.Error:
            self._proc = None
            return
        self._stdin = self._proc.get_stdin_pipe()
        self._proc.wait_async(None, self._reap, None)

        # o daemon escreve "frame" no stdout a cada PNG novo
        self._stdout = Gio.DataInputStream.new(self._proc.get_stdout_pipe())
        self._read_line()

    def _read_line(self) -> None:
        if self._stdout is None:
            return
        self._stdout.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_line)

    def _on_line(self, stream: Gio.DataInputStream, res: Gio.AsyncResult) -> None:
        try:
            line, _len = stream.read_line_finish_utf8(res)
        except GLib.Error:
            return
        if line is None:  # EOF
            return
        if line.strip() == "frame" and self._png.exists():
            self._on_frame(str(self._png))
        self._read_line()

    def _send(self, line: str) -> None:
        if self._stdin is None:
            return
        try:
            self._stdin.write_all(line.encode(), None)
        except GLib.Error:
            pass

    def request_grab(self) -> None:
        self._send("grab\n")

    def set_anim(self, enabled: bool) -> None:
        self._send("anim on\n" if enabled else "anim off\n")

    def stop(self) -> None:
        self._stdout = None
        if self._stdin is not None:
            try:
                self._stdin.close(None)
            except GLib.Error:
                pass
            self._stdin = None
        if self._proc is not None:
            try:
                self._proc.force_exit()
            except GLib.Error:
                pass
            self._proc = None

    def _reap(self, proc, result, _data) -> None:
        try:
            proc.wait_finish(result)
        except GLib.Error:
            pass
        if proc is self._proc:
            self._proc = None
