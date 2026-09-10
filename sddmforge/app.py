"""sddm-forge main window.

Layout: sidebar (sections) · settings pane · live preview.
The preview is always at hand — every change shows up in it right away — and
collapses via the header button or automatically in narrow windows.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

from . import paths, preview  # noqa: E402
from .model import SddmConfig  # noqa: E402
from .pages import GROUP_BREAK_BEFORE, ORDER, preview_pane  # noqa: E402
from .widgets import Binder  # noqa: E402

APP_ID = "br.com.maia.SddmForge"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="sddm-forge")
        self.set_default_size(1180, 760)
        self.set_size_request(360, 480)

        paths.sync_work_theme()
        self.cfg = SddmConfig.load()
        self.binder = Binder(self.mark_dirty)
        self.fullscreen_preview = preview.FullscreenPreview()
        self.live = preview.LivePreview(self._on_preview_frame, self)
        self.enable_service = False
        self._theme_write_source = 0
        self._section = ORDER[0][0]
        self._nav_rows: dict[str, Gtk.ListBoxRow] = {}

        self.connect("close-request", self._on_close)

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        self.split = Adw.NavigationSplitView(
            min_sidebar_width=200, max_sidebar_width=248,
            sidebar_width_fraction=0.2,
        )
        self.toasts.set_child(self.split)
        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())

        self._add_breakpoints()

        self._build_pages()
        self.nav.select_row(self._nav_rows[self._section])
        GLib.idle_add(lambda: (self._sync_preview(), False)[1])

    # -- shell -------------------------------------------------------------
    def _build_sidebar(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="sddm-forge", subtitle=""))
        toolbar.add_top_bar(header)

        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.add_css_class("navigation-sidebar")
        self.nav.set_header_func(self._nav_header)
        self.nav.connect("row-selected", self._on_nav_selected)

        for name, title, icon, _module in ORDER:
            row = Gtk.ListBoxRow()
            row.section = name  # type: ignore[attr-defined]
            box = Gtk.Box(spacing=12, margin_top=10, margin_bottom=10,
                          margin_start=6, margin_end=6)
            box.append(Gtk.Image(icon_name=icon))
            box.append(Gtk.Label(label=title, xalign=0))
            row.set_child(box)
            self.nav.append(row)
            self._nav_rows[name] = row

        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      vexpand=True)
        scroller.set_child(self.nav)
        toolbar.set_content(scroller)

        return Adw.NavigationPage(title="sddm-forge", child=toolbar)

    def _nav_header(self, row: Gtk.ListBoxRow, before: Gtk.ListBoxRow | None) -> None:
        want = before is not None and getattr(row, "section", "") == GROUP_BREAK_BEFORE
        has = row.get_header() is not None
        if want and not has:
            row.set_header(Gtk.Separator())
        elif not want and has:
            row.set_header(None)

    def _build_content(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()

        self.title = Adw.WindowTitle(title=ORDER[0][1], subtitle="")
        self.header.set_title_widget(self.title)

        self.apply_btn = Gtk.Button(label="Apply")
        self.apply_btn.add_css_class("suggested-action")
        # starts enabled: reinstalling the working copy to the system (backup +
        # theme + drop-in) is always a valid action. Only greys out after apply.
        self.apply_btn.set_tooltip_text("Install the working theme to the system")
        self.apply_btn.connect("clicked", lambda _b: self.on_apply())
        self.header.pack_end(self.apply_btn)

        menu = Gio.Menu()
        menu.append("Reload from system", "win.reload")
        menu.append("About", "win.about")
        self.header.pack_end(
            Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        )
        self._add_action("reload", lambda *_: self.reload_from_system())
        self._add_action("about", lambda *_: self._show_about())

        self.preview_btn = Gtk.ToggleButton(
            icon_name="sidebar-show-right-symbolic", active=True,
            tooltip_text="Show preview",
        )
        self.preview_btn.connect(
            "notify::active",
            lambda b, _p: (
                b.set_tooltip_text(
                    "Hide preview" if b.get_active() else "Show preview"
                ),
                self._sync_preview(),
            ),
        )
        self.header.pack_end(self.preview_btn)

        toolbar.add_top_bar(self.header)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            hexpand=True, vexpand=True,
        )
        self.preview_pane = preview_pane.build_pane(self)
        self.preview_btn.bind_property(
            "active", self.preview_pane, "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )

        self.paned = Gtk.Paned(
            orientation=Gtk.Orientation.HORIZONTAL,
            shrink_start_child=False, shrink_end_child=False,
            resize_start_child=True, resize_end_child=True,
            position=520,
        )
        self.stack.set_size_request(340, -1)
        self.preview_pane.set_size_request(320, -1)
        self.paned.set_start_child(self.stack)
        self.paned.set_end_child(self.preview_pane)
        self.paned.connect("map", self._balance_paned)
        toolbar.set_content(self.paned)

        return Adw.NavigationPage(title=ORDER[0][1], child=toolbar)

    def _balance_paned(self, _paned) -> None:
        # initial split: settings ~46 % (clamped to a readable range),
        # preview gets the rest. The user can drag it afterwards.
        def once() -> bool:
            width = self.paned.get_width()
            if width > 1:
                self.paned.set_position(max(440, min(680, round(width * 0.46))))
            return False
        GLib.idle_add(once)

    def _add_breakpoints(self) -> None:
        # narrow window: hide the preview (the header button still turns it on)
        bp_preview = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 1000sp")
        )
        bp_preview.add_setter(self.preview_btn, "active", False)
        self.add_breakpoint(bp_preview)

        # even narrower: the sidebar becomes a drawer
        bp_nav = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 680sp")
        )
        bp_nav.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(bp_nav)

    # -- infra ------------------------------------------------------------
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
        for name, title, _icon, module in ORDER:
            self.stack.add_titled(module.build(self), name, title)
        self.stack.set_visible_child_name(self._section)
        if self.live.is_running():
            GLib.timeout_add(150, lambda: (self.live.request_grab(), False)[1])

    def mark_dirty(self) -> None:
        self.cfg.dirty = True
        self.apply_btn.set_sensitive(True)
        self.title.set_subtitle("unapplied changes")
        self._schedule_theme_write()

    # -- navigation ------------------------------------------------------
    def _on_nav_selected(self, _list, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        self._section = row.section  # type: ignore[attr-defined]
        title = dict((n, t) for n, t, _i, _m in ORDER)[self._section]
        self.title.set_title(title)
        self.split.get_content().set_title(title)
        if self.stack.get_child_by_name(self._section) is not None:
            self.stack.set_visible_child_name(self._section)
        if self.split.get_collapsed():
            self.split.set_show_content(True)

    # -- embedded preview ----------------------------------------------
    def _write_work(self) -> None:
        self.cfg.write_work_theme_conf()
        self.cfg.write_work_layout()

    def _sync_preview(self) -> None:
        if self.preview_btn.get_active():
            self.live.start()
            self._write_work()
            GLib.timeout_add(300, lambda: (self.live.request_grab(), False)[1])
        else:
            self.live.stop()
            stack = getattr(self, "_preview_stack", None)
            if stack is not None:
                stack.set_visible_child_name("empty")

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
        preview_pane.set_frame(self, path)

    def on_fullscreen_preview(self) -> None:
        if preview.greeter_bin() is None:
            self._toast("sddm-greeter-qt6 not found (sddm package).")
            return
        self._write_work()
        try:
            self.fullscreen_preview.launch()
        except Exception as exc:  # noqa: BLE001
            self._toast(f"Failed to open: {exc}")

    def _on_close(self, *_a) -> bool:
        self.live.stop()
        self.fullscreen_preview.stop()
        return False

    def set_enable_service(self, value: bool) -> None:
        self.enable_service = value
        self.mark_dirty()

    # -- actions ------------------------------------------------------
    def reload_from_system(self) -> None:
        self.cfg = SddmConfig.load()
        self.enable_service = False
        self._build_pages()
        self.title.set_subtitle("")
        self._toast("Reloaded from system.")

    def reseed_theme(self) -> None:
        paths.reseed_work_theme()
        self._write_work()
        if self.live.is_running():
            self.live.request_grab()
        self._toast("Main.qml and assets restored from bundle.")

    def _apply_py(self) -> Path:
        return (Path(__file__).parent / "apply.py").resolve()

    def _python(self) -> str:
        return shutil.which("python3") or sys.executable

    def _run_spec(self, spec: dict, success_msg: str) -> None:
        if shutil.which("pkexec") is None:
            self._toast("pkexec not found — install the polkit package.")
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
            self._toast(f"Failed to call pkexec: {exc.message}")
            return

        self.apply_btn.set_sensitive(False)

        def on_done(p: Gio.Subprocess, res: Gio.AsyncResult) -> None:
            Path(spec_path).unlink(missing_ok=True)
            try:
                ok, _out, err = p.communicate_utf8_finish(res)
            except GLib.Error as exc:
                self._toast(f"Error: {exc.message}")
                self.apply_btn.set_sensitive(True)
                return
            if p.get_successful():
                self.title.set_subtitle("")
                self._toast(success_msg)
                self.cfg = SddmConfig.load()
                self.enable_service = False
                self._build_pages()
            else:
                msg = (err or "").strip().splitlines()
                self._toast(msg[-1] if msg else "pkexec failed or was cancelled.")
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
            "Applied. Log out or run 'systemctl restart sddm' (from a TTY) to see it.",
        )

    def restore_backup(self, path: str) -> None:
        dialog = Adw.AlertDialog(
            heading="Restore backup?",
            body=f"This overwrites the current theme and drop-in with the snapshot\n{path}",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "Restore")
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
            self._run_spec(spec, "Backup restored.")

        dialog.connect("response", on_resp)
        dialog.present(self)

    def _show_about(self) -> None:
        about = Adw.AboutDialog(
            application_name="sddm-forge",
            application_icon=APP_ID,
            developer_name="maiajota",
            version="0.1.0",
            comments="Configure SDDM and the Maia login theme.",
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
