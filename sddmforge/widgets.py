"""Helpers to build preference rows with minimal repetition."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import (  # noqa: E402
    Adw, Gdk, GdkPixbuf, GLib, GObject, Gtk, Pango,
)

_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"}
_last_browse_dir: list[Path] = []  # remembers the last folder visited


class _LazyThumb(Gtk.Frame):
    """Thumbnail that loads a downscaled pixbuf in the background (idle queue)."""

    _queue: list[tuple[_LazyThumb, str, int]] = []
    _running = False

    def __init__(self, path: str, w: int = 200, h: int = 124) -> None:
        super().__init__(overflow=Gtk.Overflow.HIDDEN)
        self.add_css_class("view")
        self._pic = Gtk.Picture(content_fit=Gtk.ContentFit.COVER,
                                can_shrink=True)
        self._pic.set_size_request(w, h)
        self._spin = Gtk.Spinner(halign=Gtk.Align.CENTER,
                                 valign=Gtk.Align.CENTER)
        self._spin.start()
        overlay = Gtk.Overlay()
        overlay.set_child(self._pic)
        overlay.add_overlay(self._spin)
        self.set_child(overlay)
        _LazyThumb._queue.append((self, path, w))
        _LazyThumb._pump()

    def _load(self, path: str, w: int) -> None:
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, w * 2, -1, True)
            self._pic.set_paintable(Gdk.Texture.new_for_pixbuf(pb))
        except GLib.Error:
            self._pic.set_paintable(None)
        self._spin.stop()
        self._spin.set_visible(False)

    @classmethod
    def _pump(cls) -> None:
        if cls._running:
            return
        cls._running = True
        GLib.idle_add(cls._step, priority=GLib.PRIORITY_DEFAULT_IDLE)

    @classmethod
    def _step(cls) -> bool:
        if not cls._queue:
            cls._running = False
            return False
        thumb, path, w = cls._queue.pop(0)
        if thumb.get_realized() or thumb.get_parent() is not None:
            thumb._load(path, w)
        return True


def _pick_start_dir() -> Path:
    if _last_browse_dir and _last_browse_dir[-1].is_dir():
        return _last_browse_dir[-1]
    h = Path.home()
    pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
    cands = []
    if pics:
        cands += [Path(pics) / "Wallpapers", Path(pics) / "wallpapers", Path(pics)]
    cands += [h / "Pictures" / "Wallpapers", h / "Pictures"]
    for cand in cands:
        if cand.is_dir():
            return cand
    return h


def _folder_browser(
    window: Gtk.Window, on_pick: Callable[[str], None],
) -> None:
    """Folder browser with thumbnails — replaces Gtk.FileChooserDialog for
    images (the native chooser only shows a file icon here, since there is no
    thumbnailer service running)."""
    dlg = Adw.Dialog()
    dlg.set_content_width(860)
    dlg.set_content_height(620)
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    title = Adw.WindowTitle(title="Choose image", subtitle="")
    header.set_title_widget(title)
    up_btn = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Parent folder")
    home_btn = Gtk.Button(icon_name="user-home-symbolic", tooltip_text="Home")
    header.pack_start(up_btn)
    header.pack_start(home_btn)
    toolbar.add_top_bar(header)

    flow = Gtk.FlowBox(
        selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
        column_spacing=10, row_spacing=10, min_children_per_line=3,
        max_children_per_line=5, valign=Gtk.Align.START,
        margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
    )
    scroller = Gtk.ScrolledWindow(
        child=flow, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
    )
    toolbar.set_content(scroller)
    dlg.set_child(toolbar)

    state = {"dir": _pick_start_dir()}

    def entry_button(child: Gtk.Widget, on_click) -> Gtk.Button:
        btn = Gtk.Button(child=child)
        btn.add_css_class("flat")
        btn.connect("clicked", lambda _b: on_click())
        return btn

    def show(folder: Path) -> None:
        state["dir"] = folder
        _last_browse_dir.clear()
        _last_browse_dir.append(folder)
        title.set_subtitle(str(folder).replace(str(Path.home()), "~"))
        up_btn.set_sensitive(folder != folder.parent)
        c = flow.get_first_child()
        while c is not None:
            nxt = c.get_next_sibling()
            flow.remove(c)
            c = nxt
        try:
            items = sorted(folder.iterdir(),
                           key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            items = []
        dirs = [p for p in items if p.is_dir() and not p.name.startswith(".")]
        imgs = [p for p in items
                if p.is_file() and p.suffix.lower() in _IMG_EXT]
        for d in dirs:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            icon = Gtk.Image.new_from_icon_name("folder-symbolic")
            icon.set_pixel_size(64)
            icon.set_size_request(200, 124)
            box.append(icon)
            lbl = Gtk.Label(label=d.name, max_width_chars=20)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.add_css_class("caption")
            box.append(lbl)
            flow.append(entry_button(box, lambda p=d: show(p)))
        for f in imgs[:150]:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.append(_LazyThumb(str(f)))
            lbl = Gtk.Label(label=f.name, max_width_chars=20)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.add_css_class("caption")
            box.append(lbl)
            flow.append(entry_button(
                box, lambda p=f: (on_pick(str(p)), dlg.close())))

    up_btn.connect("clicked", lambda _b: show(state["dir"].parent))
    home_btn.connect("clicked", lambda _b: show(Path.home()))
    show(state["dir"])
    dlg.present(window)


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


POSITION_GRID_CSS = """
.position-grid {
  padding: 4px;
  border-radius: 10px;
  background-color: alpha(currentColor, 0.07);
}
.position-grid > button {
  min-width: 42px;
  min-height: 27px;
  padding: 0;
}
"""

_SPAN_LABEL = {1: "33%", 2: "66%", 3: "fill"}


def _norm(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def _span_of(val: str) -> int:
    v = str(val or "")
    if v == "fill":
        return 3
    if v.endswith("%"):
        try:
            return min(3, max(1, round(float(v[:-1]) / 33.34)))
        except ValueError:
            return 1
    return 1  # auto, px, empty → 1 cell


def _place(anchor: str, span: int) -> tuple[int, int]:
    if anchor in ("left", "top"):
        a = 0
    elif anchor in ("right", "bottom"):
        a = 3 - span
    else:
        a = (3 - span) // 2
    return a, a + span - 1


def _region_to_props(r0, c0, r1, c1) -> tuple[str, str, str]:
    if (c0 == 0 and c1 == 2) or (0 < c0 and c1 < 2):
        hx = "center"
    else:
        hx = "left" if c0 == 0 else "right"
    if (r0 == 0 and r1 == 2) or (0 < r0 and r1 < 2):
        vy = "center"
    else:
        vy = "top" if r0 == 0 else "bottom"
    pos = "center" if hx == "center" and vy == "center" else f"{vy}-{hx}"
    # single cell = "anchor here, natural size"; rectangle = fraction of screen
    if r0 == r1 and c0 == c1:
        return pos, "auto", "auto"
    return pos, _SPAN_LABEL[c1 - c0 + 1], _SPAN_LABEL[r1 - r0 + 1]


class RegionGrid(Gtk.Grid):
    """3×3 grid mirroring the screen: tap a cell to anchor the panel there
    (natural size), or drag a rectangle to make it fill that area. The
    selected region shows in the accent color.

    Emits ``region-changed(position, width, height)``. No region = free
    position (x/y).
    """

    __gtype_name__ = "SddmForgeRegionGrid"
    __gsignals__ = {
        "region-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str)),
    }

    def __init__(self, position: str = "", width="auto", height="auto") -> None:
        super().__init__(row_spacing=3, column_spacing=3)
        self.add_css_class("position-grid")
        self._updating = False
        self._region: tuple[int, int, int, int] | None = None
        self._cells: list[list[Gtk.ToggleButton]] = []
        for r in range(3):
            rowbtns = []
            for c in range(3):
                btn = Gtk.ToggleButton()
                lbl = f"{['top', 'middle', 'bottom'][r]}, " \
                      f"{['left', 'center', 'right'][c]}"
                btn.set_tooltip_text(lbl)
                try:
                    btn.update_property([Gtk.AccessibleProperty.LABEL], [lbl])
                except (AttributeError, TypeError):
                    pass
                btn.connect("toggled", self._on_toggled, r, c)
                self.attach(btn, c, r, 1, 1)
                rowbtns.append(btn)
            self._cells.append(rowbtns)

        drag = Gtk.GestureDrag()
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        self.add_controller(drag)
        self._start_cell = None
        self._did_drag = False

        self.set_region_from_props(position, width, height)

    # -- painting ------------------------------------------------------
    def _paint(self, region) -> None:
        self._updating = True
        for r in range(3):
            for c in range(3):
                on = region is not None and (
                    region[0] <= r <= region[2] and region[1] <= c <= region[3]
                )
                btn = self._cells[r][c]
                btn.set_active(on)
                (btn.add_css_class if on else btn.remove_css_class)(
                    "suggested-action"
                )
        self._updating = False

    def _commit(self, region, emit: bool) -> None:
        self._region = region
        self._paint(region)
        if emit and region is not None:
            self.emit("region-changed", *_region_to_props(*region))

    def set_region_from_props(self, position, width, height) -> None:
        if not isinstance(position, str) or position == "":
            self._commit(None, emit=False)
            return
        if position == "center":
            vy, hx = "center", "center"
        elif "-" in position:
            vy, hx = position.split("-", 1)
        else:
            vy, hx = "top", "left"
        c0, c1 = _place(hx, _span_of(width))
        r0, r1 = _place(vy, _span_of(height))
        self._commit((r0, c0, r1, c1), emit=False)

    # -- click on a cell (mouse or keyboard) = 1×1 region --------------
    def _on_toggled(self, _btn, r: int, c: int) -> None:
        if self._updating or self._did_drag:
            return
        self._commit((r, c, r, c), emit=True)

    # -- drag = rectangle -------------------------------------------
    def _cell_at(self, x: float, y: float):
        w, h = self.get_width(), self.get_height()
        if w <= 0 or h <= 0:
            return None
        return (
            min(2, max(0, int(y * 3 / h))),
            min(2, max(0, int(x * 3 / w))),
        )

    def _drag_begin(self, _g, sx, sy) -> None:
        self._start_cell = self._cell_at(sx, sy)
        self._origin = (sx, sy)
        self._did_drag = False

    def _drag_update(self, g, ox, oy) -> None:
        if self._start_cell is None:
            return
        if not self._did_drag and ox * ox + oy * oy < 36:
            return
        self._did_drag = True
        g.set_state(Gtk.EventSequenceState.CLAIMED)
        sx, sy = self._origin
        cur = self._cell_at(sx + ox, sy + oy) or self._start_cell
        self._paint(_norm(self._start_cell, cur))

    def _drag_end(self, _g, ox, oy) -> None:
        start = self._start_cell
        self._start_cell = None
        if start is None or not self._did_drag:
            return
        sx, sy = self._origin
        cur = self._cell_at(sx + ox, sy + oy) or start
        self._commit(_norm(start, cur), emit=True)
        self._did_drag = False


class Binder:
    """Builds Adw.* rows already wired to a change callback."""

    def __init__(self, on_change: Callable[[], None]) -> None:
        self._on_change = on_change

    def _changed(self) -> None:
        self._on_change()

    def region(
        self,
        title: str,
        position: object,
        width: object,
        height: object,
        setter: Callable[[str, str, str], None],
        subtitle: str = "",
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        grid = RegionGrid(
            position if isinstance(position, str) else "",
            str(width), str(height),
        )
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_end(4)

        def on_changed(_g, pos: str, w: str, h: str) -> None:
            setter(pos, w, h)
            self._changed()

        grid.connect("region-changed", on_changed)
        row.add_suffix(grid)
        return row

    def toggles(
        self,
        title: str,
        options: list[str],
        value: str,
        setter: Callable[[str], None],
        labels: list[str] | None = None,
        subtitle: str = "",
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        group = Adw.ToggleGroup(valign=Gtk.Align.CENTER, can_shrink=False)
        for opt, lab in zip(options, labels or options):
            group.add(Adw.Toggle(name=opt, label=lab))
        if value in options:
            group.set_active_name(value)
        else:
            group.set_active(0)

        def on_notify(g, _p):
            name = g.get_active_name()
            if name in options:
                setter(name)
                self._changed()

        group.connect("notify::active", on_notify)
        row.add_suffix(group)
        row.set_activatable_widget(group)
        return row

    def chips(
        self,
        title: str,
        options: list[str],
        value: str,
        setter: Callable[[str], None],
        draw: Callable,
        labels: list[str] | None = None,
        subtitle: str = "",
    ) -> Adw.ActionRow:
        """Row of chips with a drawn schematic of each option. `draw` is
        ``fn(area, cr, w, h, key, selected)`` — the current color
        (``area.get_color()``) is already right: light on the accent when
        selected."""
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        state = {"updating": False}
        buttons: dict[str, Gtk.ToggleButton] = {}

        def select(key: str) -> None:
            for k, btn in buttons.items():
                on = k == key
                btn.set_active(on)
                (btn.add_css_class if on else btn.remove_css_class)(
                    "suggested-action"
                )
                btn.get_child().queue_draw()

        for i, opt in enumerate(options):
            area = Gtk.DrawingArea(content_width=46, content_height=28)
            area.set_draw_func(
                lambda a, cr, w, h, o=opt, bt=None: draw(
                    a, cr, w, h, o, buttons[o].get_active()
                )
            )
            btn = Gtk.ToggleButton(
                child=area,
                tooltip_text=(labels[i] if labels else opt),
            )
            try:
                btn.update_property(
                    [Gtk.AccessibleProperty.LABEL],
                    [labels[i] if labels else opt],
                )
            except (AttributeError, TypeError):
                pass

            def on_toggled(bt, o=opt) -> None:
                if state["updating"]:
                    return
                state["updating"] = True
                select(o)
                state["updating"] = False
                setter(o)
                self._changed()

            btn.connect("toggled", on_toggled)
            buttons[opt] = btn
            box.append(btn)

        state["updating"] = True
        select(value if value in buttons else options[0])
        state["updating"] = False
        row.add_suffix(box)
        return row

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
            # In-process GTK dialog (not Gtk.FileDialog via the portal): it
            # follows the app theme and does not depend on the desktop portal
            # file chooser, which on some setups routes to backends that don't
            # open or look out of place.
            dlg = Gtk.FileChooserDialog(
                title=title, transient_for=window, modal=True,
                action=Gtk.FileChooserAction.OPEN,
            )
            dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dlg.add_button("Choose", Gtk.ResponseType.ACCEPT)

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

    def image(
        self,
        title: str,
        value: str,
        setter: Callable[[str], None],
        assets_dir: Path,
        window: Gtk.Window,
    ) -> Adw.ActionRow:
        """Row with a thumbnail of the current image; opens the image browser."""
        assets_dir = Path(assets_dir)
        row = Adw.ActionRow(title=title)

        thumb = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True)
        thumb.set_size_request(64, 40)
        thumb.set_valign(Gtk.Align.CENTER)
        thumb_frame = Gtk.Frame(overflow=Gtk.Overflow.HIDDEN,
                                valign=Gtk.Align.CENTER)
        thumb_frame.add_css_class("view")
        thumb_frame.set_child(thumb)

        def _paint(val: str) -> None:
            p = assets_dir / Path(val).name if val else None
            if p and p.is_file():
                thumb.set_filename(str(p))
                thumb_frame.set_visible(True)
                row.set_subtitle(p.name)
            else:
                thumb_frame.set_visible(False)
                row.set_subtitle("none" if not val else Path(val).name)

        _paint(value)

        btn = Gtk.Button(icon_name="image-x-generic-symbolic",
                         valign=Gtk.Align.CENTER, tooltip_text="Choose image")

        def picked(src_path: str) -> None:
            src = Path(src_path)
            assets_dir.mkdir(parents=True, exist_ok=True)
            dest = assets_dir / src.name
            try:
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
            except OSError as exc:
                print("failed to copy image:", exc)
                return
            setter(f"assets/{dest.name}")
            _paint(f"assets/{dest.name}")
            self._changed()

        btn.connect(
            "clicked",
            lambda _b: _folder_browser(window, picked),
        )
        row.add_prefix(thumb_frame)
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
