"""Preview pane: live offscreen render of the theme, always visible next to
the settings.

It is no longer a sidebar section — it is ``MainWindow``'s right-hand pane,
which can be collapsed via the header button.
"""

from __future__ import annotations

from gi.repository import Adw, Gdk, GLib, Gtk

from .. import preview

_NOTE = (
    "Approximate preview: fictional users, and in video mode the background "
    "shows as a static frame. Use “Full screen” for the real render."
)
_NOTE_NO_PYSIDE = (
    "PySide6 not found — the embedded preview is unavailable. Install it with "
    "your package manager (python3-pyside6), or use “Full screen”."
)


def _screen_ratio(window) -> float:
    """Real screen aspect ratio, so the preview has no letterbox bars."""
    try:
        display = window.get_display()
        monitors = display.get_monitors()
        if monitors.get_n_items():
            geo = monitors.get_item(0).get_geometry()
            if geo.height:
                return max(1.0, geo.width / geo.height)
    except Exception:  # noqa: BLE001
        pass
    return 16 / 9


def build_pane(window) -> Gtk.Widget:
    """Build the preview pane. Stores refs on ``window`` for set_frame()."""
    pane = Adw.ToolbarView()

    # --- stage: the rendered image at screen ratio, centered --------------
    picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN)
    picture.set_can_shrink(True)
    window.preview_picture = picture

    placeholder = Gtk.Label(label="Generating preview…")
    placeholder.add_css_class("dim-label")
    placeholder.add_css_class("title-4")

    stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
    stack.add_named(placeholder, "empty")
    stack.add_named(picture, "img")
    window._preview_stack = stack

    frame = Gtk.Frame()
    frame.set_child(stack)

    stage = Gtk.AspectFrame(
        ratio=_screen_ratio(window), obey_child=False,
        xalign=0.5, yalign=0.5,
        margin_start=12, margin_end=12, margin_top=12, margin_bottom=6,
        hexpand=True, vexpand=True,
    )
    stage.set_child(frame)
    pane.set_content(stage)

    # --- action bar + caption (footer) ----------------------------------
    actions = Gtk.ActionBar()

    refresh = Gtk.Button(
        icon_name="view-refresh-symbolic", tooltip_text="Refresh now",
    )
    refresh.connect("clicked", lambda _b: window.live.request_grab())
    actions.pack_start(refresh)

    anim = Gtk.ToggleButton(
        icon_name="media-playback-start-symbolic",
        tooltip_text="Animate — re-renders ~2×/s, uses more CPU",
    )
    anim.connect("toggled", lambda b: window.live.set_anim(b.get_active()))
    actions.pack_start(anim)

    full = Gtk.Button(label="Full screen")
    full.set_tooltip_text("Opens sddm-greeter in test mode (real render, with video)")
    full.connect("clicked", lambda _b: window.on_fullscreen_preview())
    actions.pack_end(full)

    note = Gtk.Label(
        label=_NOTE if preview.live_available() else _NOTE_NO_PYSIDE,
        wrap=True, xalign=0,
        margin_start=12, margin_end=12, margin_top=2, margin_bottom=8,
    )
    note.add_css_class("caption")
    note.add_css_class("dim-label")

    footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    footer.append(actions)
    footer.append(note)
    pane.add_bottom_bar(footer)

    return pane


def set_frame(window, path: str) -> None:
    try:
        texture = Gdk.Texture.new_from_filename(path)
    except GLib.Error:
        return
    window.preview_picture.set_paintable(texture)
    stack = getattr(window, "_preview_stack", None)
    if stack is not None:
        stack.set_visible_child_name("img")
