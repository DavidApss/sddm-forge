"""Helpers para montar linhas de preferências com pouca repetição."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402


def hex_to_rgba(value: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if not rgba.parse(value or "#000000"):
        rgba.parse("#000000")
    return rgba


def rgba_to_hex(rgba: Gdk.RGBA) -> str:
    r = round(rgba.red * 255)
    g = round(rgba.green * 255)
    b = round(rgba.blue * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


class Binder:
    """Cria linhas Adw.* já conectadas a um callback de mudança."""

    def __init__(self, on_change: Callable[[], None]) -> None:
        self._on_change = on_change

    def _changed(self) -> None:
        self._on_change()

    def switch(
        self, title: str, subtitle: str, value: bool, setter: Callable[[bool], None]
    ) -> Adw.SwitchRow:
        row = Adw.SwitchRow(title=title, subtitle=subtitle, active=bool(value))

        def on_notify(r, _p):
            setter(r.get_active())
            self._changed()

        row.connect("notify::active", on_notify)
        return row

    def combo(
        self,
        title: str,
        options: list[str],
        value: str,
        setter: Callable[[str], None],
        labels: list[str] | None = None,
    ) -> Adw.ComboRow:
        model = Gtk.StringList.new(labels or options)
        row = Adw.ComboRow(title=title, model=model)
        try:
            row.set_selected(options.index(value))
        except ValueError:
            row.set_selected(0)

        def on_notify(r, _p):
            idx = r.get_selected()
            if 0 <= idx < len(options):
                setter(options[idx])
                self._changed()

        row.connect("notify::selected", on_notify)
        return row

    def spin(
        self,
        title: str,
        lo: float,
        hi: float,
        step: float,
        value: float,
        setter: Callable[[float], None],
        digits: int = 0,
    ) -> Adw.SpinRow:
        row = Adw.SpinRow.new_with_range(lo, hi, step)
        row.set_title(title)
        row.set_digits(digits)
        row.set_value(float(value))

        def on_notify(r, _p):
            v = r.get_value()
            setter(int(v) if digits == 0 else round(v, digits))
            self._changed()

        row.connect("notify::value", on_notify)
        return row

    def entry(
        self,
        title: str,
        value: str,
        setter: Callable[[str], None],
    ) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(value or "")

        def on_changed(r):
            setter(r.get_text())
            self._changed()

        row.connect("changed", on_changed)
        return row

    def color(
        self, title: str, value: str, setter: Callable[[str], None]
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title)
        btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
        btn.set_valign(Gtk.Align.CENTER)
        btn.set_rgba(hex_to_rgba(value))

        def on_notify(b, _p):
            setter(rgba_to_hex(b.get_rgba()))
            self._changed()

        btn.connect("notify::rgba", on_notify)
        row.add_suffix(btn)
        row.set_activatable_widget(btn)
        return row

    def file(
        self,
        title: str,
        value: str,
        setter: Callable[[str], None],
        window: Gtk.Window,
        theme_dir_hint: str = "",
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=value or "—")
        btn = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER)

        def on_click(_b):
            # Diálogo GTK no próprio processo (não o Gtk.FileDialog via portal):
            # segue o tema do app (escuro) e não depende do file-chooser portal
            # do desktop, que aqui roteia pra backends que não abrem ou destoam.
            dlg = Gtk.FileChooserDialog(
                title=title, transient_for=window, modal=True,
                action=Gtk.FileChooserAction.OPEN,
            )
            dlg.add_button("Cancelar", Gtk.ResponseType.CANCEL)
            dlg.add_button("Escolher", Gtk.ResponseType.ACCEPT)

            def on_resp(d, resp):
                if resp == Gtk.ResponseType.ACCEPT and d.get_file() is not None:
                    setter(d.get_file().get_path())
                    row.set_subtitle(d.get_file().get_path())
                    self._changed()
                d.destroy()

            dlg.connect("response", on_resp)
            dlg.present()

        btn.connect("clicked", on_click)
        row.add_suffix(btn)
        row.set_activatable_widget(btn)
        return row


def group(title: str, description: str = "") -> Adw.PreferencesGroup:
    return Adw.PreferencesGroup(title=title, description=description)


def page(title: str, icon: str = "") -> Adw.PreferencesPage:
    p = Adw.PreferencesPage(title=title)
    if icon:
        p.set_icon_name(icon)
    return p
