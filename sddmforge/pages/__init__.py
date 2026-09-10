"""sddm-forge configuration sections.

The preview is no longer a section: it became a fixed pane next to the
settings (see ``sddmforge.pages.preview_pane`` and ``MainWindow``). What
remains here are the five editing sections, in sidebar order.
"""

from . import appearance, clock, layout, system, themes

# (key, title, icon, module) — the module exposes build(window) -> Adw.PreferencesPage
ORDER = [
    ("appearance", "Appearance", "applications-graphics-symbolic", appearance),
    ("layout", "Layout", "view-grid-symbolic", layout),
    ("clock", "Clock", "alarm-symbolic", clock),
    ("system", "System", "applications-system-symbolic", system),
    ("themes", "Themes", "preferences-desktop-appearance-symbolic", themes),
]

# the sidebar draws a separator before this section (splits "what shows on
# screen" from "how SDDM behaves")
GROUP_BREAK_BEFORE = "system"
