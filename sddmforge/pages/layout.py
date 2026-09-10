"""Layout section: editor for the panel tree (layout.json).

Each panel is a container; you pick what goes inside, the direction, where it
sits, the blur, etc. Nothing is fixed in place.
"""

from __future__ import annotations

from gi.repository import Adw, Gdk, GObject, Gtk

from ..layout_defaults import ALIGNMENTS, LEAF_LABELS, ORIENTATIONS
from ..widgets import POSITION_GRID_CSS, group, page

_CSS = """
.dnd-above { box-shadow: inset 0 3px 0 0 @accent_bg_color; }
.dnd-below { box-shadow: inset 0 -3px 0 0 @accent_bg_color; }
.dnd-dragging { opacity: 0.4; }
.drag-handle { min-width: 24px; opacity: 0.55; }
row:hover .drag-handle { opacity: 1; }
""" + POSITION_GRID_CSS
_css_done = False


def _ensure_css():
    global _css_done
    if _css_done:
        return
    prov = Gtk.CssProvider()
    try:
        prov.load_from_string(_CSS)
    except AttributeError:
        prov.load_from_data(_CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), prov,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _css_done = True


def _drag_source(row, node_id):
    src = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
    src.connect("prepare",
                lambda _s, _x, _y: Gdk.ContentProvider.new_for_value(node_id))

    def on_begin(_s, drag):
        icon = Gtk.WidgetPaintable(widget=row)
        _s.set_icon(icon, 0, 0)
        row.add_css_class("dnd-dragging")

    src.connect("drag-begin", on_begin)
    src.connect("drag-end", lambda *_a: row.remove_css_class("dnd-dragging"))
    row.add_controller(src)


def _drop_target(row, ref_id, reorder):
    """reorder(dragged_id, ref_id, after: bool)"""
    tgt = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)

    def _after(y):
        return y > row.get_height() / 2

    def on_motion(_t, _x, y):
        below = _after(y)
        row.remove_css_class("dnd-above" if below else "dnd-below")
        row.add_css_class("dnd-below" if below else "dnd-above")
        return Gdk.DragAction.MOVE

    def on_leave(_t):
        row.remove_css_class("dnd-above")
        row.remove_css_class("dnd-below")

    def on_drop(_t, value, _x, y):
        row.remove_css_class("dnd-above")
        row.remove_css_class("dnd-below")
        if value and value != ref_id:
            reorder(value, ref_id, _after(y))
        return True

    tgt.connect("motion", on_motion)
    tgt.connect("leave", on_leave)
    tgt.connect("drop", on_drop)
    row.add_controller(tgt)

_ORIENT_LABELS = {"column": "Column", "row": "Row"}
_ALIGN_LABELS = {"start": "Start", "center": "Center", "end": "End"}
_WIDTHS = ["auto", "fill", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%"]
_WIDTH_LABELS = {"auto": "Automatic", "fill": "Full screen"}


def _icon_btn(icon, tip, cb):
    b = Gtk.Button(icon_name=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
    b.add_css_class("flat")
    b.connect("clicked", lambda _b: cb())
    return b


def _handle():
    """Drag handle — larger glyph, grab cursor on hover."""
    img = Gtk.Image(icon_name="list-drag-handle-symbolic")
    img.set_pixel_size(20)
    img.add_css_class("drag-handle")
    img.set_cursor_from_name("grab")
    img.set_tooltip_text("Drag to reorder (or move to another panel)")
    return img


# "add" palette, grouped by function (covers every LEAF_TYPE)
_ADD_GROUPS = [
    ("Clock and date", ["clock", "date"]),
    ("User", ["usernameRow", "userHandle", "avatar"]),
    ("Password and login", ["password", "passwordToggle", "loginButton",
                            "errorMessage"]),
    ("Session and power", ["sessionButton", "sessionName", "rebootButton",
                           "powerButton", "suspendButton"]),
    ("Text and spacing", ["text", "separator", "spacer"]),
]


def build(window) -> Gtk.Widget:
    _ensure_css()
    holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    def refresh():
        old = holder.get_first_child()
        if old is not None:
            holder.remove(old)
        holder.append(_render(window, refresh))

    window._layout_refresh = refresh
    refresh()
    return holder


def _render(window, refresh) -> Gtk.Widget:
    cfg = window.cfg
    b = window.binder
    p = page("Layout", "view-grid-symbolic")

    def struct(fn):
        fn()
        window.mark_dirty()
        refresh()

    def reorder(dragged, ref, after):
        struct(lambda: cfg.reorder_node(dragged, ref, after))

    top = group("Panels", "Each panel is a container; pick what goes inside")
    r = Adw.ButtonRow(title="Add panel", start_icon_name="list-add-symbolic")
    r.connect("activated", lambda _r: struct(lambda: cfg.add_panel()))
    top.add(r)
    p.add(top)

    for panel in cfg.panels():
        _panel_group(window, p, panel, struct, reorder, b, depth=0)

    g = group("Global")
    g.add(b.spin("Horizontal margin", 0, 400, 4, cfg.theme["marginX"],
                 lambda v: cfg.set_theme("marginX", v)))
    g.add(b.spin("Vertical margin", 0, 400, 4, cfg.theme["marginY"],
                 lambda v: cfg.set_theme("marginY", v)))
    g.add(b.spin("Password field width", 120, 600, 10,
                 cfg.theme["passwordWidth"],
                 lambda v: cfg.set_theme("passwordWidth", v)))
    p.add(g)
    return p


def _panel_group(window, pg_page, panel, struct, reorder, b, depth,
                 parent_name=None):
    cfg = window.cfg
    pid = panel["id"]
    name = panel.get("name") or "Panel"
    if depth > 0:
        title = "↳ Subsection: " + name
        desc = f"inside «{parent_name}»" if parent_name else ""
        rm_tip = "Remove subsection"
    else:
        title = name
        desc = ""
        rm_tip = "Remove panel"
    g = group(title, desc)

    # header: move / delete
    hb = Gtk.Box(spacing=2)
    hb.append(_icon_btn("go-up-symbolic", "Move up",
                        lambda: struct(lambda: cfg.move_node(pid, -1))))
    hb.append(_icon_btn("go-down-symbolic", "Move down",
                        lambda: struct(lambda: cfg.move_node(pid, 1))))
    hb.append(_icon_btn("user-trash-symbolic", rm_tip,
                        lambda: struct(lambda: cfg.remove_node(pid))))
    g.set_header_suffix(hb)

    name_row = b.entry("Name", panel.get("name", ""),
                       lambda v: cfg.set_node_prop(pid, "name", v))
    name_row.add_prefix(_handle())
    _drag_source(name_row, pid)
    _drop_target(name_row, pid, reorder)
    g.add(name_row)

    # Direction sits at the top level (most-used setting): column = stack,
    # row = items side by side.
    g.add(b.toggles(
        "Direction", ORIENTATIONS, panel.get("orientation", "column"),
        lambda v: cfg.set_node_prop(pid, "orientation", v),
        labels=[_ORIENT_LABELS[x] for x in ORIENTATIONS]))

    pos = panel.get("position", "top-left")
    free = pos if isinstance(pos, dict) else {}

    # --- Position and size ---------------------------------------------
    geo = Adw.ExpanderRow(title="Position and size")
    fine = Adw.ExpanderRow(
        title="Fine-tune",
        subtitle=("exact coordinates and size" if depth == 0
                  else "exact size"),
    )
    fine.set_expanded(bool(free))

    # grid: tap = anchor (natural size), drag a rectangle = fill that area.
    # Root panel only — a sub-panel flows inside its parent.
    if depth == 0:
        geo.add_row(b.region(
            "On screen", pos,
            panel.get("width", "auto"), panel.get("height", "auto"),
            lambda p, w, h: [cfg.set_node_prop(pid, "position", p),
                             cfg.set_node_prop(pid, "width", w),
                             cfg.set_node_prop(pid, "height", h)],
            subtitle="tap to anchor · drag to size"))

        # free X and Y: they share state (otherwise one never "sees" the
        # other); both filled overrides the grid.
        _free = {"x": str(free.get("x", "")), "y": str(free.get("y", ""))}

        def _set_free(axis, val):
            _free[axis] = val.strip()
            if _free["x"] != "" and _free["y"] != "":
                cfg.set_node_prop(pid, "position",
                                  {"x": _free["x"], "y": _free["y"]})
            # if either is empty: keep the grid position (leave it alone)

        fine.add_row(b.entry("X (px or %)", _free["x"],
                             lambda v: _set_free("x", v)))
        fine.add_row(b.entry("Y (px or %)", _free["y"],
                             lambda v: _set_free("y", v)))

    w = str(panel.get("width", "auto"))
    widths = _WIDTHS if w in _WIDTHS else [w, *_WIDTHS]
    fine.add_row(b.combo(
        "Width", widths, w,
        lambda v: cfg.set_node_prop(pid, "width", v),
        labels=[_WIDTH_LABELS.get(x, x) for x in widths]))
    h = str(panel.get("height", "auto"))
    heights = _WIDTHS if h in _WIDTHS else [h, *_WIDTHS]
    fine.add_row(b.combo(
        "Height", heights, h,
        lambda v: cfg.set_node_prop(pid, "height", v),
        labels=[_WIDTH_LABELS.get(x, x) for x in heights]))
    geo.add_row(fine)
    g.add(geo)

    # --- Alignment and spacing -----------------------------------------
    space = Adw.ExpanderRow(title="Alignment and spacing")
    space.add_row(b.toggles(
        "Content placement", ALIGNMENTS, panel.get("justify", "start"),
        lambda v: cfg.set_node_prop(pid, "justify", v),
        labels=["Start", "Center", "End"]))
    space.add_row(b.toggles(
        "Align children", ALIGNMENTS, panel.get("align", "start"),
        lambda v: cfg.set_node_prop(pid, "align", v),
        labels=[_ALIGN_LABELS[x] for x in ALIGNMENTS]))
    space.add_row(b.spin("Space between items", 0, 120, 2, panel.get("gap", 0),
                         lambda v: cfg.set_node_prop(pid, "gap", v)))
    _pad = panel.get("padding", 0)
    space.add_row(b.spin("Horizontal padding", 0, 400, 4,
                         panel.get("paddingX", _pad),
                         lambda v: cfg.set_node_prop(pid, "paddingX", v)))
    space.add_row(b.spin("Vertical padding", 0, 400, 4,
                         panel.get("paddingY", _pad),
                         lambda v: cfg.set_node_prop(pid, "paddingY", v)))
    g.add(space)

    # --- Panel background (glass effect) — advanced, collapsed --------
    glass = Adw.ExpanderRow(title="Panel background",
                            subtitle="blur, glass, border, corner")
    glass.add_row(b.spin("Background blur (%)", 0, 100, 5, panel.get("blur", 0),
                         lambda v: cfg.set_node_prop(pid, "blur", v)))
    glass.add_row(b.spin("Darken panel (%)", 0, 100, 5, panel.get("dim", 0),
                         lambda v: cfg.set_node_prop(pid, "dim", v)))
    _tints = ["", "#0affffff", "#16ffffff", "#24ffffff",
              "#18000000", "#33000000"]
    _tint_lbl = ["None", "Subtle glass", "Light glass", "Strong glass",
                 "Light smoke", "Strong smoke"]
    _cur_tint = panel.get("tint") or panel.get("bg") or ""
    tints = _tints if _cur_tint in _tints else [_cur_tint, *_tints]
    tlabels = _tint_lbl if _cur_tint in _tints else [_cur_tint, *_tint_lbl]
    glass.add_row(b.combo(
        "Color wash", tints, _cur_tint,
        lambda v: cfg.set_node_prop(pid, "tint", v),
        labels=tlabels))
    glass.add_row(b.spin("Grain %", 0, 100, 5, panel.get("noise", 0),
                         lambda v: cfg.set_node_prop(pid, "noise", v)))
    _borders = ["", "#33ffffff", "#59ffffff", "#33000000"]
    _border_lbl = ["None", "Light line", "Strong line", "Dark line"]
    _cb = panel.get("border", "")
    bords = _borders if _cb in _borders else [_cb, *_borders]
    blabels = _border_lbl if _cb in _borders else [_cb, *_border_lbl]
    glass.add_row(b.combo(
        "Edge line", bords, _cb,
        lambda v: cfg.set_node_prop(pid, "border", v), labels=blabels))
    glass.add_row(b.spin("Corner radius", 0, 80, 2, panel.get("radius", 0),
                         lambda v: cfg.set_node_prop(pid, "radius", v)))
    g.add(glass)

    children = panel.get("children", [])
    subpanels = []
    for child in children:
        if child.get("type") == "panel":
            subpanels.append(child)
            # marker at the right spot: shows the subsection lives here
            g.add(_subpanel_row(window, child, struct, reorder))
            continue
        g.add(_element_row(window, child, pid, struct, reorder, b))

    # --- add (elements + sub-panels in one grouped place) -------------
    def _sub(**kw):
        struct(lambda: cfg.add_panel(pid, **kw))

    _sub_opts = [
        ("Column (stacks items)", dict(orientation="column")),
        ("Row (items side by side)", dict(orientation="row")),
    ]

    add = Adw.ExpanderRow(
        title="Add to panel", subtitle="elements and sub-panels"
    )
    add.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
    # dropping onto the palette = move the piece into this panel
    _drop_into = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
    _drop_into.connect("drop", lambda _t, v, *_a: (
        v and v != pid and struct(lambda: cfg.move_into_panel(v, pid))) or True)
    add.add_controller(_drop_into)

    def _caption(text):
        row = Gtk.ListBoxRow(activatable=False, selectable=False, can_focus=False)
        lbl = Gtk.Label(label=text, xalign=0, margin_start=12,
                        margin_top=10, margin_bottom=2)
        lbl.add_css_class("caption-heading")
        lbl.add_css_class("dim-label")
        row.set_child(lbl)
        add.add_row(row)

    def _add_row(title_, on_activate):
        er = Adw.ActionRow(title=title_, activatable=True)
        er.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
        er.connect("activated", lambda _r: on_activate())
        add.add_row(er)

    for grp, types in _ADD_GROUPS:
        _caption(grp)
        for t in types:
            _add_row(LEAF_LABELS.get(t, t),
                     lambda tt=t: struct(lambda: cfg.add_element(pid, tt)))

    _caption("Split into sub-panel")
    for label_, kw in _sub_opts:
        _add_row(label_, lambda kw=kw: _sub(**kw))

    g.add(add)

    pg_page.add(g)

    for sub in subpanels:
        _panel_group(window, pg_page, sub, struct, reorder, b, depth + 1,
                     parent_name=name)


def _subpanel_row(window, node, struct, reorder):
    """Marker row shown in the parent panel's item list: makes clear the
    subsection lives there and in what order. Its editor is the group below."""
    cfg = window.cfg
    nid = node["id"]
    name = node.get("name") or "Sub-panel"
    orient = _ORIENT_LABELS.get(node.get("orientation", "column"), "").lower()
    items = [c for c in node.get("children", []) if c.get("type") != "panel"]
    n = len(items)

    row = Adw.ActionRow(
        title=name,
        subtitle=f"subsection · {orient} · {n} " + ("item" if n == 1 else "items")
        + "   ·   edit in the group below ↓",
    )
    row.add_prefix(_handle())
    row.add_prefix(Gtk.Image(icon_name="view-list-symbolic"))

    controls = Gtk.Box(spacing=2)
    controls.append(_icon_btn("go-up-symbolic", "Move up",
                              lambda: struct(lambda: cfg.move_node(nid, -1))))
    controls.append(_icon_btn("go-down-symbolic", "Move down",
                              lambda: struct(lambda: cfg.move_node(nid, 1))))
    controls.append(_icon_btn("user-trash-symbolic", "Remove subsection",
                              lambda: struct(lambda: cfg.remove_node(nid))))
    row.add_suffix(controls)

    _drag_source(row, nid)
    _drop_target(row, nid, reorder)
    return row


# elements that accept a color/bold override
_TEXTY = {"clock", "date", "text", "usernameRow", "userHandle",
          "sessionName", "errorMessage", "separator"}
# elements with their own "size" (for loginButton = width)
_SIZED = {"text": 16, "spacer": 20, "separator": 40, "avatar": 76,
          "loginButton": 140}
# "boring" elements (no props, no style) → simple row
_PLAIN = {"password", "sessionButton", "rebootButton",
          "powerButton", "suspendButton"}


def _element_row(window, node, panel_id, struct, reorder, b):
    cfg = window.cfg
    nid = node["id"]
    typ = node["type"]
    label = LEAF_LABELS.get(typ, typ)

    controls = Gtk.Box(spacing=2)
    controls.append(_icon_btn("go-up-symbolic", "Move up",
                              lambda: struct(lambda: cfg.move_node(nid, -1))))
    controls.append(_icon_btn("go-down-symbolic", "Move down",
                              lambda: struct(lambda: cfg.move_node(nid, 1))))
    controls.append(_icon_btn("user-trash-symbolic", "Remove",
                              lambda: struct(lambda: cfg.remove_node(nid))))

    def wire(row):
        row.add_prefix(_handle())
        _drag_source(row, nid)
        _drop_target(row, nid, reorder)
        return row

    if typ in _PLAIN:
        row = Adw.ActionRow(title=label)
        row.add_suffix(controls)
        return wire(row)

    row = Adw.ExpanderRow(title=label)
    row.add_suffix(controls)

    # type-specific props
    if typ in ("text", "passwordToggle", "loginButton"):
        _tlabel = "Label (empty = LOGIN)" if typ == "loginButton" else "Text"
        row.add_row(b.entry(_tlabel, node.get("text", ""),
                            lambda v: cfg.set_node_prop(nid, "text", v)))
    if typ == "usernameRow":
        row.add_row(b.switch("‹ › arrows to switch user", "",
                             node.get("carousel", True),
                             lambda v: cfg.set_node_prop(nid, "carousel", v)))
    if typ in _SIZED:
        lo, hi = (2, 600)
        title = {"separator": "Length", "loginButton": "Width"}.get(
            typ, "Size")
        row.add_row(b.spin(title, lo, hi, 2, node.get("size", _SIZED[typ]),
                           lambda v: cfg.set_node_prop(nid, "size", v)))

    # style (color / bold) — only where it makes sense
    if typ in _TEXTY:
        cur = node.get("accent", "")
        color_exp = Adw.ExpanderRow(
            title="Custom color", subtitle="otherwise follows the theme color"
        )
        color_exp.set_show_enable_switch(True)
        color_exp.set_enable_expansion(bool(cur))
        color_exp.set_expanded(bool(cur))
        color_exp.add_row(b.color("Color", cur or "#ffffff",
                                  lambda v: cfg.set_node_prop(nid, "accent", v)))

        def _on_color_toggle(exp, _p):
            on = exp.get_enable_expansion()
            has = bool(cfg.node(nid).get("accent"))
            if on:
                exp.set_expanded(True)
                if not has:
                    cfg.set_node_prop(nid, "accent", "#ffffff")
                    window.mark_dirty()
            elif has:
                cfg.set_node_prop(nid, "accent", "")
                window.mark_dirty()

        color_exp.connect("notify::enable-expansion", _on_color_toggle)
        row.add_row(color_exp)
        if typ not in ("separator",):
            row.add_row(b.switch("Bold", "", bool(node.get("bold")),
                                 lambda v: cfg.set_node_prop(nid, "bold", v)))

    return wire(row)
