from __future__ import annotations
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UserRole(Enum):
    # Blado — un seul rôle
    RH = 'RH'  # Responsable des Ressources Humaines


class ConnMode(Enum):
    INTRANET = 'Intranet'
    CLOUD    = 'Cloud'
    OFFLINE  = 'Hors connexion'


@dataclass
class AuthResult:
    user_id   : int      = 0
    email     : str      = ''
    full_name : str      = ''
    role      : UserRole = field(default_factory=lambda: UserRole.RH)
    term_id   : int      = 0
    term_label: str      = ''
    fk_language: int     = 2


@dataclass
class Session:
    # BLADO: ajout mode et entreprise_id + sync
    user_id          : int                = 0
    email            : str                = ''
    full_name        : str                = ''
    role             : UserRole           = field(default_factory=lambda: UserRole.RH)
    conn_mode        : Optional[ConnMode] = None
    is_authenticated : bool               = False
    instance_dir     : str                = ''
    mode             : str                = 'RH'        # 'RH' ou 'consultant'
    entreprise_id    : int                = 0           # entreprise active (mode consultant)
    term_id          : int                = 0
    term_label       : str                = ''
    fk_language      : int                = 2
    theme_pref       : str                = 'blue'
    card_theme       : str                = 'medium'
    type_flags       : dict               = field(default_factory=dict)
    role_flags       : dict               = field(default_factory=dict)


session: Session = Session(
    instance_dir=os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    )
)
