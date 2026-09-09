"""Páginas de configuração do sddm-forge."""

from . import (
    aparencia,
    autologin,
    backup,
    layout,
    previa,
    relogio,
    sddm,
    temas,
    usuarios,
)

ORDER = [
    ("previa", "Prévia", previa),
    ("aparencia", "Aparência", aparencia),
    ("layout", "Layout", layout),
    ("relogio", "Relógio", relogio),
    ("sddm", "SDDM", sddm),
    ("autologin", "Autologin", autologin),
    ("usuarios", "Usuários", usuarios),
    ("temas", "Temas", temas),
    ("backup", "Backup", backup),
]
