"""Configuration model: reads/writes theme.conf and the SDDM drop-in."""

from __future__ import annotations

import base64
import binascii
import configparser
import glob
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .layout_defaults import default_layout, normalize_layout

# ---------------------------------------------------------------------------
# Theme key spec ([General] section of theme.conf).
# (default, type) — type in {"str", "bool", "int", "float"}
# ---------------------------------------------------------------------------
THEME_SPEC: dict[str, tuple[object, str]] = {
    "backgroundMode": ("video", "str"),        # video | image | color
    "background": ("assets/background.jpeg", "str"),
    "backgroundVideo": ("assets/frieren-moon.mp4", "str"),
    "bgColor": ("#0b0f14", "str"),
    "blurRadius": (24, "int"),
    "videoBlurRadius": (4, "int"),
    "dimOpacity": (0.40, "float"),

    "accentColor": ("#66d9ff", "str"),
    "accentColorDim": ("#55aacc", "str"),
    "textColor": ("#ffffff", "str"),
    "subTextColor": ("#b0c7d8", "str"),
    "errorColor": ("#ff8080", "str"),

    "fontFamily": ("JetBrains Mono", "str"),
    "clockFontSize": (68, "int"),
    "dateFontSize": (18, "int"),
    "nameFontSize": (26, "int"),

    "marginX": (56, "int"),
    "marginY": (56, "int"),
    "passwordWidth": (280, "int"),

    "clockFormat": ("hh:mm", "str"),
    "dateFormat": ("dddd, MMMM d", "str"),
    "dateLocale": ("en_US", "str"),

    # widget styles
    "inputStyle": ("underline", "str"),    # underline | box | pill | segmented
    "buttonStyle": ("outline", "str"),     # outline | fill | pill   (login)
    "controlStyle": ("text", "str"),       # text | outline | pill   (session/power)
    "controlIcons": ("off", "str"),        # off | only | label
}

INPUT_STYLES = ["underline", "box", "pill", "segmented"]
BUTTON_STYLES = ["outline", "fill", "pill"]
CONTROL_STYLES = ["text", "outline", "pill"]
CONTROL_ICONS = ["off", "only", "label"]

BACKGROUND_MODES = ["video", "image", "color"]

# ---------------------------------------------------------------------------
# SDDM drop-in spec (/etc/sddm.conf.d/10-maia.conf).
# section -> {key: default}
# ---------------------------------------------------------------------------
SDDM_SPEC: dict[str, dict[str, str]] = {
    "Theme": {
        "Current": paths.THEME_NAME,
        "CursorTheme": "",
        "Font": "",
    },
    "General": {
        "Numlock": "none",  # none | on | off
    },
    "Autologin": {
        "User": "",
        "Session": "",
        "Relogin": "false",
    },
    "Users": {
        "MinimumUid": "1000",
        "MaximumUid": "60000",
        "HideUsers": "",
        "HideShells": "",
    },
    "Wayland": {
        "EnableHiDPI": "true",
    },
}

NUMLOCK_VALUES = ["none", "on", "off"]


def _coerce(raw: str, typ: str) -> object:
    raw = (raw or "").strip()
    if typ == "bool":
        return raw.lower() == "true"
    if typ == "int":
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return 0
    if typ == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    return raw


def _fmt(value: object, typ: str) -> str:
    if typ == "bool":
        return "true" if value else "false"
    if typ == "float":
        return f"{float(value):.2f}"
    return str(value)


@dataclass
class SddmConfig:
    theme: dict[str, object] = field(default_factory=dict)
    sddm: dict[str, dict[str, str]] = field(default_factory=dict)
    layout: dict = field(default_factory=default_layout)
    dirty: bool = False

    # -- construction ----------------------------------------------------
    @classmethod
    def defaults(cls) -> "SddmConfig":
        theme = {k: v[0] for k, v in THEME_SPEC.items()}
        sddm = {sec: dict(keys) for sec, keys in SDDM_SPEC.items()}
        return cls(theme=theme, sddm=sddm, layout=default_layout())

    @classmethod
    def load(cls) -> "SddmConfig":
        cfg = cls.defaults()
        work = paths.ensure_work_theme()
        cfg._load_theme(work / "theme.conf")
        cfg._load_layout(work / "layout.json")
        cfg._load_sddm()
        cfg.dirty = False
        return cfg

    def _load_layout(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if isinstance(data, dict) and isinstance(data.get("root"), list):
            self.layout = normalize_layout(data)

    def _load_theme(self, conf_path: Path) -> None:
        if not conf_path.is_file():
            return
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str  # keep key capitalization
        try:
            parser.read(conf_path, encoding="utf-8")
        except configparser.Error:
            return
        if not parser.has_section("General"):
            return
        for key, (_default, typ) in THEME_SPEC.items():
            if parser.has_option("General", key):
                self.theme[key] = _coerce(parser.get("General", key), typ)
        if parser.has_option("General", "layoutJson"):
            raw = parser.get("General", "layoutJson").strip()
            text = raw
            if raw and not raw.lstrip().startswith("{"):
                try:  # base64 (SDDM strips quotes from theme.conf values)
                    text = base64.b64decode(raw).decode("utf-8")
                except (binascii.Error, UnicodeDecodeError, ValueError):
                    text = raw
            try:
                data = json.loads(text)
                if isinstance(data, dict) and isinstance(data.get("root"), list):
                    self.layout = normalize_layout(data)
            except (json.JSONDecodeError, TypeError):
                pass

    def _load_sddm(self) -> None:
        files: list[Path] = []
        if paths.SDDM_CONF.is_file():
            files.append(paths.SDDM_CONF)
        if paths.SDDM_CONF_D.is_dir():
            files += sorted(Path(p) for p in glob.glob(str(paths.SDDM_CONF_D / "*.conf")))
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        for f in files:
            try:
                parser.read(f, encoding="utf-8")
            except configparser.Error:
                continue
        for sec, keys in SDDM_SPEC.items():
            for key in keys:
                if parser.has_option(sec, key):
                    self.sddm[sec][key] = parser.get(sec, key).strip()

    # -- serialization ------------------------------------------------
    def theme_conf_text(self) -> str:
        lines = [
            "[General]",
            "# Generated by sddm-forge. Edited via the GUI.",
            "",
        ]
        for key, (_default, typ) in THEME_SPEC.items():
            lines.append(f"{key}={_fmt(self.theme.get(key, _default), typ)}")
        # layout embedded as base64 — SDDM strips quotes from theme.conf values,
        # so raw JSON does not survive. base64 is only [A-Za-z0-9+/=]. The
        # greeter and the preview read it via `config.layoutJson`; the
        # layout.json alongside is just for inspection.
        compact = json.dumps(self.layout, separators=(",", ":"), ensure_ascii=False)
        b64 = base64.b64encode(compact.encode("utf-8")).decode("ascii")
        lines += ["", f"layoutJson={b64}"]
        return "\n".join(lines) + "\n"

    def dropin_text(self) -> str:
        out: list[str] = ["# Generated by sddm-forge — do not edit by hand.", ""]
        for sec, keys in SDDM_SPEC.items():
            body: list[str] = []
            for key in keys:
                val = self.sddm.get(sec, {}).get(key, "").strip()
                if val == "":
                    continue
                if sec == "General" and key == "Numlock" and val == "none":
                    continue
                body.append(f"{key}={val}")
            if body:
                out.append(f"[{sec}]")
                out.extend(body)
                out.append("")
        return "\n".join(out).rstrip() + "\n"

    def layout_json_text(self) -> str:
        return json.dumps(self.layout, indent=2, ensure_ascii=False) + "\n"

    def write_work_theme_conf(self) -> Path:
        work = paths.ensure_work_theme()
        conf = work / "theme.conf"
        conf.write_text(self.theme_conf_text(), encoding="utf-8")
        return conf

    def write_work_layout(self) -> Path:
        work = paths.ensure_work_theme()
        path = work / "layout.json"
        path.write_text(self.layout_json_text(), encoding="utf-8")
        return path

    # -- layout tree -------------------------------------------------
    def panels(self) -> list[dict]:
        return self.layout.setdefault("root", [])

    def _find(self, node_id: str, children: list[dict] | None = None,
              parent: dict | None = None):
        """Returns (node, siblings_list) or (None, None)."""
        siblings = self.panels() if children is None else children
        for node in siblings:
            if node.get("id") == node_id:
                return node, siblings
            if node.get("type") == "panel":
                found, lst = self._find(node_id, node.get("children", []), node)
                if found is not None:
                    return found, lst
        return None, None

    def node(self, node_id: str) -> dict | None:
        return self._find(node_id)[0]

    def set_node_prop(self, node_id: str, key: str, value: object) -> None:
        n = self.node(node_id)
        if n is not None:
            n[key] = value
            self.dirty = True

    # back-compat aliases
    def panel(self, panel_id: str) -> dict | None:
        return self.node(panel_id)

    def set_panel_prop(self, panel_id: str, key: str, value: object) -> None:
        self.set_node_prop(panel_id, key, value)

    def add_panel(
        self,
        parent_id: str | None = None,
        *,
        orientation: str = "column",
        name: str | None = None,
        child_types: list[str] | None = None,
    ) -> dict:
        from .layout_defaults import make_leaf, make_panel
        n = len(self.panels()) + 1
        panel = make_panel(name or f"Panel {n}", orientation=orientation)
        if orientation == "row":
            panel["align"] = "center"
            panel["gap"] = panel.get("gap") or 22
        for t in child_types or []:
            panel.setdefault("children", []).append(make_leaf(t))
        if parent_id is None:
            self.panels().append(panel)
        else:
            parent = self.node(parent_id)
            if parent is None or parent.get("type") != "panel":
                return panel
            if name is None:
                panel["name"] = "Split" if orientation == "row" else "Sub-panel"
            parent.setdefault("children", []).append(panel)
        self.dirty = True
        return panel

    def add_element(self, panel_id: str, type_: str) -> dict | None:
        from .layout_defaults import make_leaf
        parent = self.node(panel_id)
        if parent is None or parent.get("type") != "panel":
            return None
        leaf = make_leaf(type_)
        parent.setdefault("children", []).append(leaf)
        self.dirty = True
        return leaf

    def remove_node(self, node_id: str) -> None:
        node, siblings = self._find(node_id)
        if node is not None:
            siblings.remove(node)
            self.dirty = True

    def move_node(self, node_id: str, delta: int) -> None:
        node, siblings = self._find(node_id)
        if node is None:
            return
        i = siblings.index(node)
        j = i + delta
        if 0 <= j < len(siblings):
            siblings.insert(j, siblings.pop(i))
            self.dirty = True

    def move_into_panel(self, node_id: str, panel_id: str) -> None:
        if node_id == panel_id:
            return
        node, src = self._find(node_id)
        target = self.node(panel_id)
        if node is None or target is None or target.get("type") != "panel":
            return
        if node.get("type") == "panel" and self._contains(node, panel_id):
            return
        src.remove(node)
        target.setdefault("children", []).append(node)
        self.dirty = True

    def _contains(self, node: dict, node_id: str) -> bool:
        if node.get("id") == node_id:
            return True
        return any(self._contains(c, node_id) for c in node.get("children", []))

    def reorder_node(self, node_id: str, target_id: str, after: bool) -> None:
        """Move `node_id` to right before/after `target_id` (may cross
        panels). Ignored if target == node or target is inside the node."""
        if node_id == target_id:
            return
        node, src_siblings = self._find(node_id)
        target, dst_siblings = self._find(target_id)
        if node is None or target is None:
            return
        if node.get("type") == "panel" and self._contains(node, target_id):
            return
        # a leaf can't become a sibling of a root panel — drop it inside
        if (node.get("type") != "panel" and dst_siblings is self.panels()
                and target.get("type") == "panel"):
            src_siblings.remove(node)
            target.setdefault("children", []).append(node)
            self.dirty = True
            return
        src_siblings.remove(node)
        idx = dst_siblings.index(target)
        dst_siblings.insert(idx + 1 if after else idx, node)
        self.dirty = True

    # -- access helpers ------------------------------------------------
    def get_sddm(self, section: str, key: str) -> str:
        return self.sddm.get(section, {}).get(key, "")

    def set_sddm(self, section: str, key: str, value: str) -> None:
        self.sddm.setdefault(section, {})[key] = value
        self.dirty = True

    def set_theme(self, key: str, value: object) -> None:
        self.theme[key] = value
        self.dirty = True
