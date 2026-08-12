from bladocommon.app_config import AppConfig
from bladocommon.auth import AuthManager, OAuth2Manager, _sha256_hex
from bladocommon.config_loader import find_cfg
from bladocommon.database import Database, DBMode
from bladocommon.event_helpers import event_color, event_icon  # noqa: F401
from bladocommon.l10n import Translator, _  # noqa: F401
from bladocommon.logger import get_log_path, log, set_log_filename, set_log_to_file  # noqa: F401
from bladocommon.network import NetworkMode, detect_network  # noqa: F401
from bladocommon.photos import ensure_cached, get_photo_path, get_uncached_ids  # noqa: F401
from bladocommon.session import AuthResult, ConnMode, Session, UserRole
from bladocommon.theme import DesignTokens, FontScale, Palette, QssHelper, Theme, ThemeManager
from bladocommon.widgets import (
    CARD_THEMES,
    DEFAULT_CONFIG,
    PHI_COMPACT,
    PHI_LARGE,
    PHI_MEDIUM,
    CardConfig,
    FilePanel,
    FileResolver,
    FileViewer,
    StudentCard,
    TableSettings,
    fill_cards_grid,
    make_avatar,
)

__all__ = [
    "Database",
    "DBMode",
    "OAuth2Manager",
    "_deduce_role_superviseur",
    "_load_active_term",
    "Session",
    "UserRole",
    "ConnMode",
    "AuthResult",
    "find_cfg",
    "AppConfig",
    "log",
    "set_log_to_file",
    "get_log_path",
    "set_log_filename",
    "NetworkMode",
    "detect_network",
    "get_photo_path",
    "ensure_cached",
    "get_uncached_ids",
    "ThemeManager",
    "Theme",
    "Palette",
    "FontScale",
    "DesignTokens",
    "QssHelper",
    "event_icon",
    "event_color",
    "Translator",
    "_",
    "StudentCard",
    "CardConfig",
    "make_avatar",
    "fill_cards_grid",
    "PHI_COMPACT",
    "PHI_MEDIUM",
    "PHI_LARGE",
    "CARD_THEMES",
    "DEFAULT_CONFIG",
    "FileViewer",
    "FilePanel",
    "FileResolver",
    "TableSettings",
]
