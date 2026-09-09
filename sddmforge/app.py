"""Janela principal do sddm-forge."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import paths, preview  # noqa: E402
from .model import SddmConfig  # noqa: E402
from .pages import ORDER  # noqa: E402
from .widgets import Binder  # noqa: E402

APP_ID = "br.com.maia.SddmForge"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="sddm-forge")
        self.set_default_size(940, 720)

        paths.sync_work_theme()
        self.cfg = SddmConfig.load()
        self.binder = Binder(self.mark_dirty)
        self.fullscreen_preview = preview.FullscreenPreview()
        self.live = preview.LivePreview(self._on_preview_frame, self)
        self.enable_service = False
        self._theme_write_source = 0

        self.connect("close-request", self._on_close)

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        toolbar = Adw.ToolbarView()
        self.toasts.set_child(toolbar)

        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        self.title_widget = Adw.WindowTitle(title="sddm-forge", subtitle="")
        header.set_title_widget(self.title_widget)

        self.apply_btn = Gtk.Button(label="Aplicar")
        self.apply_btn.add_css_class("suggested-action")
        # começa habilitado: instalar a cópia de trabalho no sistema é sempre
        # uma ação válida (faz backup + reinstala tema e drop-in), mesmo sem
        # ter mexido em nada nesta sessão. Só volta a ficar cinza após aplicar.
        self.apply_btn.set_tooltip_text("Instala o tema de trabalho no sistema")
        self.apply_btn.connect("clicked", lambda _b: self.on_apply())
        header.pack_end(self.apply_btn)

        menu = Gio.Menu()
        menu.append("Recarregar do sistema", "win.reload")
        menu.append("Sobre", "win.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        self._add_action("reload", lambda *_: self.reload_from_system())
        self._add_action("about", lambda *_: self._show_about())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar.set_content(body)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE, hexpand=True, vexpand=True
        )
        sidebar = Gtk.StackSidebar(stack=self.stack)
        sidebar.set_size_request(190, -1)
        body.append(sidebar)
        body.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        body.append(self.stack)

        self._build_pages()
        self.stack.connect("notify::visible-child-name", self._on_page_changed)
        # a primeira aba ("previa") já está visível — dispara o start na mão
        GLib.idle_add(lambda: (self._on_page_changed(), False)[1])

    # -- infra -----------------------------------------------------------
    def _add_action(self, name: str, cb) -> None:
        act = Gio.SimpleAction.new(name, None)
        act.connect("activate", cb)
        self.add_action(act)

    def _toast(self, text: str, timeout: int = 4) -> None:
        self.toasts.add_toast(Adw.Toast(title=text, timeout=timeout))

    def _build_pages(self) -> None:
        while (child := self.stack.get_first_child()) is not None:
            self.stack.remove(child)
        self.binder = Binder(self.mark_dirty)
        for name, title, module in ORDER:
            page_widget = module.build(self)
            self.stack.add_titled(page_widget, name, title)
        if self.live.is_running():
            GLib.timeout_add(150, lambda: (self.live.request_grab(), False)[1])

    def mark_dirty(self) -> None:
        self.cfg.dirty = True
        self.apply_btn.set_sensitive(True)
        self.title_widget.set_subtitle("alterações não aplicadas")
        self._schedule_theme_write()

    # -- prévia embutida ----------------------------------------------
    def _write_work(self) -> None:
        self.cfg.write_work_theme_conf()
        self.cfg.write_work_layout()

    def _on_page_changed(self, *_a) -> None:
        if self.stack.get_visible_child_name() == "previa":
            self.live.start()
            self._write_work()
            GLib.timeout_add(300, lambda: (self.live.request_grab(), False)[1])

    def _schedule_theme_write(self) -> None:
        if self._theme_write_source:
            GLib.source_remove(self._theme_write_source)
        self._theme_write_source = GLib.timeout_add(250, self._do_theme_write)

    def _do_theme_write(self) -> bool:
        self._theme_write_source = 0
        self._write_work()
        if self.live.is_running():
            GLib.timeout_add(120, lambda: (self.live.request_grab(), False)[1])
        return False

    def _on_preview_frame(self, path: str) -> None:
        from .pages import previa
        previa.set_frame(self, path)

    def on_fullscreen_preview(self) -> None:
        if preview.greeter_bin() is None:
            self._toast("sddm-greeter-qt6 não encontrado (pacote sddm).")
            return
        self._write_work()
        try:
            self.fullscreen_preview.launch()
        except Exception as exc:  # noqa: BLE001
            self._toast(f"Falha ao abrir: {exc}")

    def _on_close(self, *_a) -> bool:
        self.live.stop()
        self.fullscreen_preview.stop()
        return False

    def set_enable_service(self, value: bool) -> None:
        self.enable_service = value
        self.mark_dirty()

    # -- ações ----------------------------------------------------------
    def reload_from_system(self) -> None:
        self.cfg = SddmConfig.load()
        self.enable_service = False
        self._build_pages()
        self.title_widget.set_subtitle("")
        self._toast("Recarregado do sistema.")

    def reseed_theme(self) -> None:
        paths.reseed_work_theme()
        self._write_work()
        if self.live.is_running():
            self.live.request_grab()
        self._toast("Main.qml e assets restaurados do embutido.")

    def _apply_py(self) -> Path:
        return (Path(__file__).parent / "apply.py").resolve()

    def _python(self) -> str:
        return shutil.which("python3") or sys.executable

    def _run_spec(self, spec: dict, success_msg: str) -> None:
        if shutil.which("pkexec") is None:
            self._toast("pkexec não encontrado — instale o pacote polkit.")
            return

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
            dir=GLib.get_user_runtime_dir() or None,
        )
        json.dump(spec, tmp)
        tmp.close()
        spec_path = tmp.name

        argv = ["pkexec", self._python(), str(self._apply_py()), spec_path]
        try:
            launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.STDERR_PIPE)
            proc = launcher.spawnv(argv)
        except GLib.Error as exc:
            Path(spec_path).unlink(missing_ok=True)
            self._toast(f"Falha ao chamar pkexec: {exc.message}")
            return

        self.apply_btn.set_sensitive(False)

        def on_done(p: Gio.Subprocess, res: Gio.AsyncResult) -> None:
            Path(spec_path).unlink(missing_ok=True)
            try:
                ok, _out, err = p.communicate_utf8_finish(res)
            except GLib.Error as exc:
                self._toast(f"Erro: {exc.message}")
                self.apply_btn.set_sensitive(True)
                return
            if p.get_successful():
                self.title_widget.set_subtitle("")
                self._toast(success_msg)
                self.cfg = SddmConfig.load()
                self.enable_service = False
                self._build_pages()
            else:
                msg = (err or "").strip().splitlines()
                self._toast(msg[-1] if msg else "pkexec falhou ou foi cancelado.")
                self.apply_btn.set_sensitive(True)

        proc.communicate_utf8_async(None, None, on_done)

    def on_apply(self) -> None:
        self._write_work()
        spec = {
            "work_theme_dir": str(paths.work_theme_dir()),
            "dropin_text": self.cfg.dropin_text(),
            "enable_service": bool(self.enable_service),
            "restore_from": None,
        }
        self._run_spec(
            spec,
            "Aplicado. Faça logout ou 'systemctl restart sddm' (num TTY) para ver.",
        )

    def restore_backup(self, path: str) -> None:
        dialog = Adw.AlertDialog(
            heading="Restaurar backup?",
            body=f"Vai sobrescrever o tema e o drop-in atuais com o snapshot\n{path}",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Restaurar")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_resp(_d, resp):
            if resp != "ok":
                return
            spec = {
                "work_theme_dir": str(paths.work_theme_dir()),
                "dropin_text": self.cfg.dropin_text(),
                "enable_service": False,
                "restore_from": path,
            }
            self._run_spec(spec, "Backup restaurado.")

        dialog.connect("response", on_resp)
        dialog.present(self)

    def _show_about(self) -> None:
        about = Adw.AboutDialog(
            application_name="sddm-forge",
            application_icon=APP_ID,
            developer_name="maiajota",
            version="0.1.0",
            comments="Configurador do SDDM e do tema Maia.",
        )
        about.present(self)


class SddmForgeApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        win = self.props.active_window or MainWindow(self)
        win.present()


def main() -> int:
    return SddmForgeApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
