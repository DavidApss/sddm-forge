"""Página Layout: editor da árvore de painéis (layout.json).

Cada painel é um contêiner; você escolhe o que colocar dentro, a direção,
onde fica, o blur, etc. Sem itens pré-fixados.
"""

from __future__ import annotations

from gi.repository import Adw, Gdk, GObject, Gtk

from ..layout_defaults import (
    ALIGNMENTS,
    LEAF_LABELS,
    LEAF_TYPES,
    ORIENTATIONS,
    PANEL_POSITIONS,
)
from ..widgets import group, page

_CSS = """
.dnd-above { box-shadow: inset 0 3px 0 0 @accent_bg_color; }
.dnd-below { box-shadow: inset 0 -3px 0 0 @accent_bg_color; }
.dnd-dragging { opacity: 0.4; }
"""
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

_POS_LABELS = {
    "top-left": "Superior esquerda", "top-center": "Superior centro",
    "top-right": "Superior direita",
    "center-left": "Centro esquerda", "center": "Centro",
    "center-right": "Centro direita",
    "bottom-left": "Inferior esquerda", "bottom-center": "Inferior centro",
    "bottom-right": "Inferior direita",
}
_ORIENT_LABELS = {"column": "Coluna", "row": "Linha"}
_ALIGN_LABELS = {"start": "Início", "center": "Centro", "end": "Fim"}
_WIDTHS = ["auto", "fill", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%"]
_WIDTH_LABELS = {"auto": "Automática", "fill": "Tela inteira"}


def _icon_btn(icon, tip, cb):
    b = Gtk.Button(icon_name=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
    b.add_css_class("flat")
    b.connect("clicked", lambda _b: cb())
    return b


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

    top = group("Painéis", "Cada painel é um contêiner; escolha o que vai dentro")
    r = Adw.ButtonRow(title="Adicionar painel", start_icon_name="list-add-symbolic")
    r.connect("activated", lambda _r: struct(lambda: cfg.add_panel()))
    top.add(r)
    p.add(top)

    for panel in cfg.panels():
        _panel_group(window, p, panel, struct, reorder, b, depth=0)

    g = group("Global")
    g.add(b.spin("Margem horizontal", 0, 400, 4, cfg.theme["marginX"],
                 lambda v: cfg.set_theme("marginX", v)))
    g.add(b.spin("Margem vertical", 0, 400, 4, cfg.theme["marginY"],
                 lambda v: cfg.set_theme("marginY", v)))
    g.add(b.spin("Largura do campo de senha", 120, 600, 10,
                 cfg.theme["passwordWidth"],
                 lambda v: cfg.set_theme("passwordWidth", v)))
    p.add(g)
    return p


def _panel_group(window, pg_page, panel, struct, reorder, b, depth,
                 parent_name=None):
    cfg = window.cfg
    pid = panel["id"]
    name = panel.get("name") or "Painel"
    if depth > 0:
        title = "↳ Subseção: " + name
        desc = f"dentro de «{parent_name}»" if parent_name else ""
        rm_tip = "Remover subseção"
    else:
        title = name
        desc = ""
        rm_tip = "Remover painel"
    g = group(title, desc)

    # cabeçalho: mover / apagar
    hb = Gtk.Box(spacing=2)
    hb.append(_icon_btn("go-up-symbolic", "Subir",
                        lambda: struct(lambda: cfg.move_node(pid, -1))))
    hb.append(_icon_btn("go-down-symbolic", "Descer",
                        lambda: struct(lambda: cfg.move_node(pid, 1))))
    hb.append(_icon_btn("user-trash-symbolic", rm_tip,
                        lambda: struct(lambda: cfg.remove_node(pid))))
    g.set_header_suffix(hb)

    name_row = b.entry("Nome", panel.get("name", ""),
                       lambda v: cfg.set_node_prop(pid, "name", v))
    name_row.add_prefix(Gtk.Image(icon_name="list-drag-handle-symbolic"))
    _drag_source(name_row, pid)
    _drop_target(name_row, pid, reorder)
    g.add(name_row)

    # Direção fica no nível de cima (é o ajuste mais usado): coluna = empilha,
    # linha = itens lado a lado.
    g.add(b.combo(
        "Direção", ORIENTATIONS, panel.get("orientation", "column"),
        lambda v: cfg.set_node_prop(pid, "orientation", v),
        labels=[_ORIENT_LABELS[x] for x in ORIENTATIONS]))

    look = Adw.ExpanderRow(title="Aparência do painel")
    pos = panel.get("position", "top-left")
    free = pos if isinstance(pos, dict) else {}

    # Posição / X-Y livre só valem pro painel raiz — um sub-painel flui dentro
    # do pai (a direção do pai é que manda).
    if depth == 0:
        look.add_row(b.combo(
            "Posição", PANEL_POSITIONS,
            pos if isinstance(pos, str) else "center",
            lambda v: cfg.set_node_prop(pid, "position", v),
            labels=[_POS_LABELS[x] for x in PANEL_POSITIONS]))

        # X e Y livre compartilham este estado (senão um só nunca "vê" o outro)
        _free = {"x": str(free.get("x", "")), "y": str(free.get("y", ""))}

        def _set_free(axis, val):
            _free[axis] = val.strip()
            if _free["x"] != "" and _free["y"] != "":
                cfg.set_node_prop(pid, "position",
                                  {"x": _free["x"], "y": _free["y"]})
            # se algum vazio: mantém a posição da combo (não mexe)

        look.add_row(b.entry("X livre (px ou %)", _free["x"],
                             lambda v: _set_free("x", v)))
        look.add_row(b.entry("Y livre (px ou %)", _free["y"],
                             lambda v: _set_free("y", v)))
    w = str(panel.get("width", "auto"))
    widths = _WIDTHS if w in _WIDTHS else [w, *_WIDTHS]
    look.add_row(b.combo(
        "Largura", widths, w,
        lambda v: cfg.set_node_prop(pid, "width", v),
        labels=[_WIDTH_LABELS.get(x, x) for x in widths]))
    h = str(panel.get("height", "auto"))
    heights = _WIDTHS if h in _WIDTHS else [h, *_WIDTHS]
    look.add_row(b.combo(
        "Altura", heights, h,
        lambda v: cfg.set_node_prop(pid, "height", v),
        labels=[_WIDTH_LABELS.get(x, x) for x in heights]))
    look.add_row(b.combo(
        "Encaixe do conteúdo", ALIGNMENTS, panel.get("justify", "start"),
        lambda v: cfg.set_node_prop(pid, "justify", v),
        labels=["Início", "Centro", "Fim"]))
    look.add_row(b.combo(
        "Alinhar filhos", ALIGNMENTS, panel.get("align", "start"),
        lambda v: cfg.set_node_prop(pid, "align", v),
        labels=[_ALIGN_LABELS[x] for x in ALIGNMENTS]))
    look.add_row(b.spin("Espaço entre itens", 0, 120, 2, panel.get("gap", 0),
                        lambda v: cfg.set_node_prop(pid, "gap", v)))
    _pad = panel.get("padding", 0)
    look.add_row(b.spin("Recuo horizontal", 0, 400, 4,
                        panel.get("paddingX", _pad),
                        lambda v: cfg.set_node_prop(pid, "paddingX", v)))
    look.add_row(b.spin("Recuo vertical", 0, 400, 4,
                        panel.get("paddingY", _pad),
                        lambda v: cfg.set_node_prop(pid, "paddingY", v)))
    look.add_row(b.spin("Blur do fundo (%)", 0, 100, 5, panel.get("blur", 0),
                        lambda v: cfg.set_node_prop(pid, "blur", v)))
    look.add_row(b.spin("Escurecer painel (%)", 0, 100, 5, panel.get("dim", 0),
                        lambda v: cfg.set_node_prop(pid, "dim", v)))
    _tints = ["", "#0affffff", "#16ffffff", "#24ffffff",
              "#18000000", "#33000000"]
    _tint_lbl = ["Nenhuma", "Vidro sutil", "Vidro claro", "Vidro forte",
                 "Fumê leve", "Fumê forte"]
    _cur_tint = panel.get("tint") or panel.get("bg") or ""
    tints = _tints if _cur_tint in _tints else [_cur_tint, *_tints]
    tlabels = _tint_lbl if _cur_tint in _tints else [_cur_tint, *_tint_lbl]
    look.add_row(b.combo(
        "Lavagem de cor (vidro)", tints, _cur_tint,
        lambda v: cfg.set_node_prop(pid, "tint", v),
        labels=tlabels))
    look.add_row(b.spin("Granulado (vidro) %", 0, 100, 5, panel.get("noise", 0),
                        lambda v: cfg.set_node_prop(pid, "noise", v)))
    _borders = ["", "#33ffffff", "#59ffffff", "#33000000"]
    _border_lbl = ["Nenhum", "Filete claro", "Filete forte", "Filete escuro"]
    _cb = panel.get("border", "")
    bords = _borders if _cb in _borders else [_cb, *_borders]
    blabels = _border_lbl if _cb in _borders else [_cb, *_border_lbl]
    look.add_row(b.combo(
        "Filete de borda (vidro)", bords, _cb,
        lambda v: cfg.set_node_prop(pid, "border", v), labels=blabels))
    look.add_row(b.spin("Canto arredondado", 0, 80, 2, panel.get("radius", 0),
                        lambda v: cfg.set_node_prop(pid, "radius", v)))
    g.add(look)

    children = panel.get("children", [])
    subpanels = []
    for child in children:
        if child.get("type") == "panel":
            subpanels.append(child)
            # marcador na ordem certa: mostra que a subseção mora aqui
            g.add(_subpanel_row(window, child, struct, reorder))
            continue
        g.add(_element_row(window, child, pid, struct, reorder, b))

    # adicionar elemento (paleta) — também aceita soltar aqui = "pra dentro"
    add_el = Adw.ExpanderRow(title="Adicionar elemento")
    _drop_into = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
    _drop_into.connect("drop", lambda _t, v, *_a: (
        v and v != pid and struct(lambda: cfg.move_into_panel(v, pid))) or True)
    add_el.add_controller(_drop_into)
    for t in LEAF_TYPES:
        er = Adw.ActionRow(title=LEAF_LABELS.get(t, t), activatable=True)
        er.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
        er.connect("activated",
                   lambda _r, tt=t: struct(lambda: cfg.add_element(pid, tt)))
        add_el.add_row(er)
    g.add(add_el)

    # sub-painel (divisão) — coluna, linha, ou presets prontos
    sp = Adw.ExpanderRow(title="Adicionar sub-painel",
                         subtitle="um contêiner dentro deste painel")
    sp.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))

    def _sub(**kw):
        struct(lambda: cfg.add_panel(pid, **kw))

    _sub_opts = [
        ("Coluna (empilha os itens)", dict(orientation="column")),
        ("Linha (itens lado a lado)", dict(orientation="row")),
        ("Linha: sessão · reiniciar · desligar",
         dict(orientation="row", name="Botões (sessão/energia)",
              child_types=["sessionButton", "rebootButton", "powerButton"])),
        ("Linha: reiniciar · desligar · suspender",
         dict(orientation="row", name="Energia",
              child_types=["rebootButton", "powerButton", "suspendButton"])),
    ]
    for title, kw in _sub_opts:
        er = Adw.ActionRow(title=title, activatable=True)
        er.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
        er.connect("activated", lambda _r, kw=kw: _sub(**kw))
        sp.add_row(er)
    g.add(sp)

    pg_page.add(g)

    for sub in subpanels:
        _panel_group(window, pg_page, sub, struct, reorder, b, depth + 1,
                     parent_name=name)


def _subpanel_row(window, node, struct, reorder):
    """Linha-marcador que aparece na lista de itens do painel pai: deixa claro
    que a subseção mora ali e em que ordem. O editor dela é o grupo logo abaixo."""
    cfg = window.cfg
    nid = node["id"]
    name = node.get("name") or "Sub-painel"
    orient = _ORIENT_LABELS.get(node.get("orientation", "column"), "").lower()
    items = [c for c in node.get("children", []) if c.get("type") != "panel"]
    n = len(items)

    row = Adw.ActionRow(
        title=name,
        subtitle=f"subseção · {orient} · {n} " + ("item" if n == 1 else "itens")
        + "   ·   edite no grupo abaixo ↓",
    )
    row.add_prefix(Gtk.Image(icon_name="list-drag-handle-symbolic"))
    row.add_prefix(Gtk.Image(icon_name="view-list-symbolic"))

    controls = Gtk.Box(spacing=2)
    controls.append(_icon_btn("go-up-symbolic", "Subir",
                              lambda: struct(lambda: cfg.move_node(nid, -1))))
    controls.append(_icon_btn("go-down-symbolic", "Descer",
                              lambda: struct(lambda: cfg.move_node(nid, 1))))
    controls.append(_icon_btn("user-trash-symbolic", "Remover subseção",
                              lambda: struct(lambda: cfg.remove_node(nid))))
    row.add_suffix(controls)

    _drag_source(row, nid)
    _drop_target(row, nid, reorder)
    return row


# elementos que aceitam override de cor/negrito
_TEXTY = {"clock", "date", "text", "usernameRow", "userHandle",
          "sessionName", "errorMessage", "separator"}
# elementos com "tamanho" próprio
_SIZED = {"text": 16, "spacer": 20, "separator": 40, "avatar": 76}
# elementos "chatos" (sem props, sem estilo) → linha simples
_PLAIN = {"password", "loginButton", "sessionButton", "rebootButton",
          "powerButton", "suspendButton"}


def _element_row(window, node, panel_id, struct, reorder, b):
    cfg = window.cfg
    nid = node["id"]
    typ = node["type"]
    label = LEAF_LABELS.get(typ, typ)

    controls = Gtk.Box(spacing=2)
    controls.append(_icon_btn("go-up-symbolic", "Subir",
                              lambda: struct(lambda: cfg.move_node(nid, -1))))
    controls.append(_icon_btn("go-down-symbolic", "Descer",
                              lambda: struct(lambda: cfg.move_node(nid, 1))))
    controls.append(_icon_btn("user-trash-symbolic", "Remover",
                              lambda: struct(lambda: cfg.remove_node(nid))))

    def wire(row):
        row.add_prefix(Gtk.Image(icon_name="list-drag-handle-symbolic"))
        _drag_source(row, nid)
        _drop_target(row, nid, reorder)
        return row

    if typ in _PLAIN:
        row = Adw.ActionRow(title=label)
        row.add_suffix(controls)
        return wire(row)

    row = Adw.ExpanderRow(title=label)
    row.add_suffix(controls)

    # props específicas
    if typ in ("text", "passwordToggle"):
        row.add_row(b.entry("Texto", node.get("text", ""),
                            lambda v: cfg.set_node_prop(nid, "text", v)))
    if typ == "usernameRow":
        row.add_row(b.switch("Setas ‹ › para trocar de usuário", "",
                             node.get("carousel", True),
                             lambda v: cfg.set_node_prop(nid, "carousel", v)))
    if typ in _SIZED:
        lo, hi = (2, 400)
        title = "Comprimento" if typ == "separator" else "Tamanho"
        row.add_row(b.spin(title, lo, hi, 2, node.get("size", _SIZED[typ]),
                           lambda v: cfg.set_node_prop(nid, "size", v)))

    # estilo (cor / negrito) — só onde faz sentido
    if typ in _TEXTY:
        cur = node.get("accent", "")
        sw = b.switch("Cor personalizada", "", bool(cur),
                      lambda v: cfg.set_node_prop(nid, "accent",
                                                  "#ffffff" if v else ""))
        row.add_row(sw)
        row.add_row(b.color("Cor", cur or "#ffffff",
                            lambda v: cfg.set_node_prop(nid, "accent", v)))
        if typ not in ("separator",):
            row.add_row(b.switch("Negrito", "", bool(node.get("bold")),
                                 lambda v: cfg.set_node_prop(nid, "bold", v)))

    return wire(row)
