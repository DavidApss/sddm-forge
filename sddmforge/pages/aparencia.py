"""Página Aparência: fundo, blur, cores, fonte."""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import paths
from ..model import (
    BACKGROUND_MODES,
    BUTTON_STYLES,
    CONTROL_ICONS,
    CONTROL_STYLES,
    INPUT_STYLES,
)
from ..widgets import group, page

_MODE_LABELS = ["Vídeo", "Imagem", "Cor sólida"]
_INPUT_LABELS = {"underline": "Sublinhado", "box": "Caixa",
                 "pill": "Pílula", "segmented": "Barra segmentada"}
_BTN_LABELS = {"outline": "Contorno", "fill": "Preenchido", "pill": "Pílula"}
_CTL_LABELS = {"text": "Texto", "outline": "Contorno", "pill": "Pílula"}
_ICON_LABELS = {"off": "Sem ícone", "only": "Só ícone", "label": "Ícone + texto"}


def _import_asset(src_path: str) -> str:
    """Copia o arquivo escolhido para assets/ da cópia de trabalho."""
    src = Path(src_path)
    assets = paths.work_theme_dir() / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    dest = assets / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return f"assets/{src.name}"


def build(window) -> "object":
    cfg = window.cfg
    b = window.binder
    p = page("Aparência", "applications-graphics-symbolic")

    g_bg = group("Fundo")
    g_bg.add(
        b.combo(
            "Modo",
            BACKGROUND_MODES,
            cfg.theme["backgroundMode"],
            lambda v: cfg.set_theme("backgroundMode", v),
            labels=_MODE_LABELS,
        )
    )
    g_bg.add(
        b.file(
            "Imagem de fundo",
            cfg.theme["background"],
            lambda v: cfg.set_theme("background", _import_asset(v)),
            window,
        )
    )
    g_bg.add(
        b.file(
            "Vídeo de fundo",
            cfg.theme["backgroundVideo"],
            lambda v: cfg.set_theme("backgroundVideo", _import_asset(v)),
            window,
        )
    )
    g_bg.add(b.color("Cor sólida / base", cfg.theme["bgColor"],
                     lambda v: cfg.set_theme("bgColor", v)))
    g_bg.add(b.spin("Blur (imagem)", 0, 128, 1, cfg.theme["blurRadius"],
                    lambda v: cfg.set_theme("blurRadius", v)))
    g_bg.add(b.spin("Blur (vídeo)", 0, 64, 1, cfg.theme["videoBlurRadius"],
                    lambda v: cfg.set_theme("videoBlurRadius", v)))
    g_bg.add(b.spin("Escurecimento", 0.0, 1.0, 0.05, cfg.theme["dimOpacity"],
                    lambda v: cfg.set_theme("dimOpacity", v), digits=2))
    p.add(g_bg)

    g_col = group("Cores")
    for key, title in [
        ("accentColor", "Destaque"),
        ("accentColorDim", "Destaque (apagado)"),
        ("textColor", "Texto"),
        ("subTextColor", "Texto secundário"),
        ("errorColor", "Erro"),
    ]:
        g_col.add(b.color(title, cfg.theme[key],
                          lambda v, k=key: cfg.set_theme(k, v)))
    p.add(g_col)

    g_font = group("Tipografia")
    g_font.add(b.entry("Fonte", cfg.theme["fontFamily"],
                       lambda v: cfg.set_theme("fontFamily", v)))
    g_font.add(b.spin("Tamanho do relógio", 16, 200, 1, cfg.theme["clockFontSize"],
                      lambda v: cfg.set_theme("clockFontSize", v)))
    g_font.add(b.spin("Tamanho da data", 8, 64, 1, cfg.theme["dateFontSize"],
                      lambda v: cfg.set_theme("dateFontSize", v)))
    g_font.add(b.spin("Tamanho do nome", 10, 80, 1, cfg.theme["nameFontSize"],
                      lambda v: cfg.set_theme("nameFontSize", v)))
    p.add(g_font)

    g_st = group("Estilo dos widgets")
    g_st.add(b.combo("Campo de senha", INPUT_STYLES, cfg.theme["inputStyle"],
                     lambda v: cfg.set_theme("inputStyle", v),
                     labels=[_INPUT_LABELS[x] for x in INPUT_STYLES]))
    g_st.add(b.combo("Botão LOGIN", BUTTON_STYLES, cfg.theme["buttonStyle"],
                     lambda v: cfg.set_theme("buttonStyle", v),
                     labels=[_BTN_LABELS[x] for x in BUTTON_STYLES]))
    g_st.add(b.combo("Botões de sessão / energia", CONTROL_STYLES,
                     cfg.theme["controlStyle"],
                     lambda v: cfg.set_theme("controlStyle", v),
                     labels=[_CTL_LABELS[x] for x in CONTROL_STYLES]))
    g_st.add(b.combo("Ícones nos botões de energia", CONTROL_ICONS,
                     cfg.theme["controlIcons"],
                     lambda v: cfg.set_theme("controlIcons", v),
                     labels=[_ICON_LABELS[x] for x in CONTROL_ICONS]))
    p.add(g_st)

    return p
