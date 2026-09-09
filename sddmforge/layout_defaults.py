"""Schema e layout padrão da tela de login (árvore de componentes).

layout.json / theme.conf[General].layoutJson
===========================================
{
  "version": 1,
  "root": [ <painel>, <painel>, ... ]      // pintados nesta ordem
}

Painel (type = "panel")
-----------------------
  id           str      identificador único (gerado)
  name         str      rótulo exibido na GUI
  type         "panel"
  orientation  "column" | "row"            // empilha vertical ou horizontal
  position     "top-left" | "top-center" | "top-right"
             | "center"
             | "bottom-left" | "bottom-center" | "bottom-right"
             | {"x": <n|"n%">, "y": <n|"n%">}   // canto sup-esq do painel
  width        "auto" | "fill" | "<n>%" | "<n>"     // n = px
  height       "auto" | "fill" | "<n>%" | "<n>"
  align        "start" | "center" | "end"      // alinhamento dos filhos no eixo cruzado
  gap          int      espaço entre filhos (px)
  padding      int      recuo interno (px)
  blur         0..100   desfoque do fundo atrás do painel
  dim          0..100   escurecimento sobre o painel
  bg           ""|"#rrggbb"|"#aarrggbb"      cor de fundo do painel
  radius       int      canto arredondado (px)
  children     [ <painel> | <folha> ]

Folha
-----
  id     str
  type   um de:
    clock date usernameRow userHandle password
    loginButton sessionButton rebootButton powerButton errorMessage
    text spacer
  props por tipo:
    usernameRow : carousel (bool, setas ‹ ›)
    text        : text (str), size (int)
    spacer      : size (int)

Posições absolutas e tamanhos aceitam "%" (relativo à tela) ou número puro (px).
"""

from __future__ import annotations

import copy
import secrets

_PANEL_KEYS = {
    "name": "",
    "orientation": "column",
    "position": "top-left",
    "width": "auto",
    "height": "auto",
    "align": "start",     # eixo cruzado (dos filhos)
    "justify": "start",    # eixo principal (bloco de conteúdo no painel)
    "gap": 0,
    "paddingX": 0,
    "paddingY": 0,
    "blur": 0,
    "dim": 0,          # escurece (preto)
    "tint": "",        # lavagem de cor translúcida — ""|"#aarrggbb"|"#rrggbb"
    "noise": 0,        # granulado (efeito vidro/acrílico) 0..100
    "bg": "",          # cor de fundo (mesma coisa que tint, mantido p/ compat)
    "border": "",      # filete de borda — ""|"#aarrggbb"
    "borderWidth": 1,
    "radius": 0,
}

# folhas e seus props extras (com default)
LEAF_PROPS: dict[str, dict[str, object]] = {
    "clock": {},
    "date": {},
    "usernameRow": {"carousel": True},
    "userHandle": {},
    "avatar": {"size": 76},
    "password": {},
    "passwordToggle": {"text": "Mostrar senha"},
    "loginButton": {},
    "sessionButton": {},
    "sessionName": {},
    "rebootButton": {},
    "powerButton": {},
    "suspendButton": {},
    "errorMessage": {},
    "text": {"text": "Texto", "size": 16},
    "separator": {"size": 40},
    "spacer": {"size": 20},
}
LEAF_TYPES = list(LEAF_PROPS)

LEAF_LABELS = {
    "clock": "Relógio (hora)",
    "date": "Data / dia da semana",
    "usernameRow": "Nome do usuário",
    "userHandle": "@usuario",
    "avatar": "Foto do usuário",
    "password": "Campo de senha",
    "passwordToggle": "Mostrar senha (checkbox)",
    "loginButton": "Botão LOGIN",
    "sessionButton": "Seletor de sessão",
    "sessionName": "Nome da sessão (texto)",
    "rebootButton": "Botão reiniciar",
    "powerButton": "Botão desligar",
    "suspendButton": "Botão suspender",
    "errorMessage": "Mensagem de erro",
    "text": "Texto livre",
    "separator": "Separador (linha)",
    "spacer": "Espaçador",
}

PANEL_POSITIONS = [
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right",
]
ORIENTATIONS = ["column", "row"]
ALIGNMENTS = ["start", "center", "end"]


def new_id() -> str:
    return "n" + secrets.token_hex(4)


def make_leaf(type_: str) -> dict:
    node = {"id": new_id(), "type": type_}
    node.update(copy.deepcopy(LEAF_PROPS.get(type_, {})))
    return node


def make_panel(name: str = "Painel", **over) -> dict:
    node = {"id": new_id(), "type": "panel"}
    node.update(copy.deepcopy(_PANEL_KEYS))
    node["name"] = name
    node.update(over)
    node.setdefault("children", [])
    return node


def _seed() -> dict:
    controls = make_panel(
        "Sessão / energia", orientation="row", position="top-left",
        align="center", gap=26,
    )
    controls["children"] = [
        make_leaf("sessionButton"), make_leaf("rebootButton"),
        make_leaf("powerButton"),
    ]
    clock = make_panel(
        "Relógio", orientation="column", position="top-right", gap=4,
    )
    clock["children"] = [make_leaf("date"), make_leaf("clock")]

    login = make_panel(
        "Login", orientation="column", position="bottom-left", gap=14,
    )
    login["children"] = [
        make_leaf("usernameRow"), make_leaf("userHandle"),
        make_leaf("password"), make_leaf("loginButton"),
        make_leaf("errorMessage"),
    ]
    return {"version": 1, "root": [controls, clock, login]}


def default_layout() -> dict:
    return _seed()


def normalize_panel(node: dict) -> dict:
    if node.get("type") != "panel":
        # folha — preserva overrides (accent/size/bold) que não estão no spec
        out = dict(node)
        out["id"] = node.get("id") or new_id()
        out["type"] = node.get("type", "text")
        for key, dflt in LEAF_PROPS.get(out["type"], {}).items():
            out.setdefault(key, dflt)
        return out
    out = {"id": node.get("id") or new_id(), "type": "panel"}
    for key, dflt in _PANEL_KEYS.items():
        out[key] = node.get(key, dflt)
    # migração: 'padding' único -> paddingX / paddingY
    if "padding" in node:
        out["paddingX"] = node.get("paddingX", node["padding"])
        out["paddingY"] = node.get("paddingY", node["padding"])
    out["children"] = [normalize_panel(c) for c in node.get("children", [])]
    return out


def normalize_layout(tree: dict) -> dict:
    return {
        "version": tree.get("version", 1),
        "root": [normalize_panel(p) for p in tree.get("root", [])],
    }
