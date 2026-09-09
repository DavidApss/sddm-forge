"""Página Prévia: render offscreen do tema, ao vivo."""

from __future__ import annotations

from gi.repository import Gdk, GLib, Gtk

from .. import preview


def build(window) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    # --- barra de ações -------------------------------------------------
    bar = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
        margin_top=8, margin_bottom=8, margin_start=12, margin_end=12,
    )
    refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Atualizar")
    refresh.connect("clicked", lambda _b: window.live.request_grab())
    bar.append(refresh)

    anim = Gtk.ToggleButton(
        icon_name="media-playback-start-symbolic",
        tooltip_text="Animar (regrava ~2×/s; usa mais CPU)",
    )
    anim.connect("toggled", lambda b: window.live.set_anim(b.get_active()))
    bar.append(anim)

    bar.append(Gtk.Box(hexpand=True))

    full = Gtk.Button(label="Abrir em tela cheia")
    full.set_tooltip_text("sddm-greeter-qt6 em modo de teste (render real, com vídeo)")
    full.connect("clicked", lambda _b: window.on_fullscreen_preview())
    bar.append(full)
    box.append(bar)

    # --- área da imagem ------------------------------------------------
    frame = Gtk.Frame(margin_start=12, margin_end=12, margin_bottom=8,
                      vexpand=True, hexpand=True)
    frame.add_css_class("view")

    picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN)
    picture.set_size_request(480, 300)
    window.preview_picture = picture

    placeholder = Gtk.Label(label="Gerando prévia…", vexpand=True)
    placeholder.add_css_class("dim-label")

    stack = Gtk.Stack()
    stack.add_named(placeholder, "empty")
    stack.add_named(picture, "img")
    window._preview_stack = stack
    frame.set_child(stack)
    box.append(frame)

    # --- rodapé -------------------------------------------------------
    note = Gtk.Label(
        label=(
            "Prévia aproximada — usuários fictícios; o vídeo de fundo aparece "
            "como um frame estático. Use “tela cheia” para o render real."
        ),
        wrap=True, xalign=0, margin_start=12, margin_end=12, margin_bottom=10,
    )
    note.add_css_class("dim-label")
    note.add_css_class("caption")
    if not preview.live_available():
        note.set_label(
            "PySide6 não encontrado — prévia embutida indisponível. "
            "Instale com: sudo dnf install python3-pyside6"
        )
    box.append(note)

    return box


def set_frame(window, path: str) -> None:
    try:
        texture = Gdk.Texture.new_from_filename(path)
    except GLib.Error:
        return
    window.preview_picture.set_paintable(texture)
    if getattr(window, "_preview_stack", None) is not None:
        window._preview_stack.set_visible_child_name("img")
