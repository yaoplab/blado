from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QObject

from phibuilder import PhiBuilder
from phibuilder.phi.scale import PhiScale
from phibuilder.theme import Theme as PhiTheme
from phibuilder.theme import ThemeConfig


class _LarcM3Colors:
    """Mappe Palette (bladocommon) vers les propriétés M3 attendues par les widgets phibuilder."""

    def __init__(self, p: "Palette"):
        self.primary = p.primary
        self.on_primary = p.on_primary
        self.primary_container = p.primary_container
        self.on_primary_container = p.text_strong
        self.secondary = p.secondary
        self.on_secondary = p.on_secondary
        self.secondary_container = p.primary_container
        self.on_secondary_container = p.text_strong
        self.tertiary = p.tertiary
        self.on_tertiary = p.on_tertiary
        self.tertiary_container = p.tertiary_container
        self.error = p.error
        self.on_error = p.on_error
        self.error_container = p.error_container
        self.surface = p.surface
        self.on_surface = p.text_strong
        self.surface_variant = p.surface_variant
        self.on_surface_variant = p.text_soft
        self.background = p.background
        self.on_background = p.text_strong
        self.outline = p.outline
        self.outline_variant = p.outline_variant
        self.surface_container = p.surface_variant
        self.surface_container_highest = p.surface_variant
        self.surface_container_low = p.surface
        self.inverse_surface = p.text_soft
        self.inverse_on_surface = p.surface
        self.inverse_primary = p.primary


THEMES_CONFIG = [
    ("blue", "Bleu", "#1565C0", False),
    ("dark", "Dark", "#212121", True),
    ("sobre", "Sobre", "#37474F", False),
    ("contrast", "Contrasté", "#0033A0", False),
]

_SEED_MAP = {k: s for k, _, s, _ in THEMES_CONFIG}
_IS_DARK_MAP = {k: d for k, _, _, d in THEMES_CONFIG}

_THEME_DESIGN = {
    "dark": dict(
        radius=6,
        radius_lg=10,
        radius_xl=14,
        field_pad_v=10,
        field_pad_h=14,
        btn_sm_pad_v=8,
        btn_sm_pad_h=18,
        btn_pad_v=10,
        btn_pad_h=22,
    ),
    "contrast": dict(
        radius=6,
        radius_lg=10,
        radius_xl=14,
        spacing=8,
        margin=20,
        field_pad_v=10,
        field_pad_h=16,
        label_pad_v=8,
        btn_pad_v=10,
        btn_pad_h=24,
        btn_sm_pad_v=8,
        btn_sm_pad_h=18,
        btn_border=2,
    ),
}


@dataclass
class Palette:
    primary: str = "#1565C0"
    on_primary: str = "#FFFFFF"
    primary_container: str = "#BBDEFB"
    secondary: str = "#00897B"
    on_secondary: str = "#FFFFFF"
    secondary_container: str = "#B2DFDB"
    tertiary: str = "#E65100"
    on_tertiary: str = "#FFFFFF"
    tertiary_container: str = "#FFCC80"
    error: str = "#C62828"
    on_error: str = "#FFFFFF"
    error_container: str = "#FFCDD2"
    surface: str = "#F5F7FA"
    surface_variant: str = "#E8EAF6"
    background: str = "#F5F7FA"
    outline: str = "#546E7A"
    outline_variant: str = "#B0BEC5"
    text_strong: str = "#1B1B1F"
    text_soft: str = "#455A64"
    text_disabled: str = "#90A4AE"
    success: str = "#2E7D32"
    active: str = "#1565C0"
    inactive: str = "#90A4AE"
    border: str = "#B0BEC5"
    border_light: str = "#E0E0E0"


@dataclass
class DesignTokens:
    radius: int = 4
    radius_lg: int = 8
    radius_xl: int = 12
    spacing: int = 8      # M3 ×8 grid standard (était 6 — n'appartenait à aucun système)
    margin: int = 16
    field_pad_v: int = 8
    field_pad_h: int = 12
    label_pad_v: int = 6
    label_pad_h: int = 0
    btn_pad_v: int = 8
    btn_pad_h: int = 20
    btn_sm_pad_v: int = 6
    btn_sm_pad_h: int = 16
    btn_border: int = 1


_THEME_PALETTES = {
    "blue": Palette(
        primary="#1565C0",
        on_primary="#FFFFFF",
        primary_container="#D1E4FF",
        secondary="#565E71",
        on_secondary="#FFFFFF",
        secondary_container="#DAE2F9",
        tertiary="#705575",
        on_tertiary="#FFFFFF",
        tertiary_container="#F8D8FF",
        error="#BA1A1A",
        on_error="#FFFFFF",
        error_container="#FFDAD6",
        success="#2E7D32",
        surface="#F8F9FF",
        surface_variant="#DFE2EB",
        background="#F8F9FF",
        outline="#74777F",
        outline_variant="#C4C6CF",
        text_strong="#191C20",
        text_soft="#43474E",
        text_disabled="#93969C",
        active="#1565C0",
        inactive="#93969C",
        border="#C4C6CF",
        border_light="#DFE2EB",
    ),
    "dark": Palette(
        primary="#64B5F6",
        on_primary="#0D2137",
        primary_container="#1E3A5F",
        secondary="#81C784",
        on_secondary="#1B3A1B",
        secondary_container="#2E5C2E",
        tertiary="#FFB74D",
        on_tertiary="#3E2C00",
        tertiary_container="#5C4300",
        error="#EF9A9A",
        on_error="#5C1A1A",
        error_container="#7C2020",
        success="#81C784",
        surface="#1E1E1E",
        surface_variant="#2D2D2D",
        background="#121212",
        outline="#616161",
        outline_variant="#424242",
        text_strong="#E0E0E0",
        text_soft="#9E9E9E",
        text_disabled="#616161",
        active="#64B5F6",
        inactive="#616161",
        border="#424242",
        border_light="#383838",
    ),
    "sobre": Palette(
        primary="#37474F",
        on_primary="#FFFFFF",
        primary_container="#CFD8DC",
        secondary="#546E7A",
        on_secondary="#FFFFFF",
        secondary_container="#B0BEC5",
        tertiary="#78909C",
        on_tertiary="#FFFFFF",
        tertiary_container="#CFD8DC",
        error="#BF360C",
        on_error="#FFFFFF",
        error_container="#FFCCBC",
        success="#33691E",
        surface="#FAFAFA",
        surface_variant="#EEEEEE",
        background="#FFFFFF",
        outline="#BDBDBD",
        outline_variant="#E0E0E0",
        text_strong="#212121",
        text_soft="#616161",
        text_disabled="#9E9E9E",
        active="#37474F",
        inactive="#BDBDBD",
        border="#E0E0E0",
        border_light="#EEEEEE",
    ),
    "contrast": Palette(
        primary="#0033A0",
        on_primary="#FFFFFF",
        primary_container="#80B3FF",
        secondary="#005A9E",
        on_secondary="#FFFFFF",
        secondary_container="#80D0FF",
        tertiary="#C62828",
        on_tertiary="#FFFFFF",
        tertiary_container="#FFB3B3",
        error="#B71C1C",
        on_error="#FFFFFF",
        error_container="#FFCDD2",
        success="#1B5E20",
        surface="#FFFFFF",
        surface_variant="#D6E8FF",
        background="#FFFFFF",
        outline="#000000",
        outline_variant="#333333",
        text_strong="#000000",
        text_soft="#1A1A1A",
        text_disabled="#555555",
        active="#0033A0",
        inactive="#666666",
        border="#000000",
        border_light="#333333",
    ),
}


@dataclass
class FontScale:
    base: int = 12
    small: int = 10
    title: int = 14
    header: int = 16
    button: int = 12
    multiplier: float = 1.0


@dataclass
class ImageScale:
    """Tailles standard des images, logos, icônes (Fibonacci + usage)."""

    logo: int = 89  # SpacingToken.GIANT
    logo_small: int = 55  # SpacingToken.HUGE
    avatar: int = 150
    photo: int = 150
    add_btn: int = 100
    icon_btn: int = 18
    icon_menu: int = 18
    icon_large: int = 32
    profile_btn: int = 34
    theme_btn: int = 34
    refresh_btn: int = 34
    field_height: int = 56  # M3TextField par défaut


@dataclass
class Theme:
    name: str
    label: str
    palette: Palette = field(default_factory=Palette)
    fonts: FontScale = field(default_factory=FontScale)
    design: DesignTokens = field(default_factory=DesignTokens)


_BUILTIN_THEMES: dict[str, Theme] = {}


def _init_themes():
    if _BUILTIN_THEMES:
        return
    for key, label, seed, is_dark in THEMES_CONFIG:
        pal = _THEME_PALETTES[key]
        dt_kwargs = _THEME_DESIGN.get(key, {})
        dt = DesignTokens(**dt_kwargs)
        _BUILTIN_THEMES[key] = Theme(key, label, pal, design=dt)


class ThemeManager(QObject):
    theme_changed = Signal()

    def __init__(self):
        super().__init__()
        _init_themes()
        self._themes = _BUILTIN_THEMES
        self._active: str = "blue"
        self._theme: Theme = self._themes[self._active]
        self._app: Optional[QApplication] = None
        self._phibuilder: Optional[PhiBuilder] = None
        self._phi_theme: Optional[PhiTheme] = None
        self._image_scale = ImageScale()

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def phibuilder(self) -> Optional[PhiBuilder]:
        return self._phibuilder

    @property
    def palette(self) -> Palette:
        return self._theme.palette

    @property
    def phi_theme(self) -> PhiTheme:
        """Thème phibuilder unifié avec les couleurs de la palette bladocommon active."""
        if self._phi_theme is None:
            cfg = ThemeConfig(
                seed_color=_SEED_MAP.get(self._active, "#1565C0"),
                is_dark=_IS_DARK_MAP.get(self._active, False),
                font_family="Segoe UI",
            )
            self._phi_theme = PhiTheme(cfg)
            self._phi_theme.spacing = PhiScale(base_spacing=4)
        self._phi_theme.colors = _LarcM3Colors(self._theme.palette)
        return self._phi_theme

    @property
    def typography(self):
        """Typographie M3 depuis le thème phibuilder actif."""
        return self.phi_theme.typo

    @property
    def fonts(self) -> FontScale:
        return self._theme.fonts

    @property
    def design(self) -> DesignTokens:
        return self._theme.design

    @property
    def image(self) -> ImageScale:
        return self._image_scale

    @property
    def active_name(self) -> str:
        return self._active

    def names(self) -> list[tuple[str, str]]:
        return [(k, v.label) for k, v in self._themes.items()]

    def get_palette(self, name: str) -> Optional[Palette]:
        t = self._themes.get(name)
        return t.palette if t else None

    def set_active(self, name: str) -> bool:
        if name in self._themes:
            self._active = name
            self._theme = self._themes[name]
            self._phi_theme = None
            self._sync_phibuilder()
            self._reapply()
            self.theme_changed.emit()
            return True
        return False

    def font_size(self, base: int) -> int:
        return max(7, int(base * self._theme.fonts.multiplier))

    def font(self, base: int, weight=QFont.Weight.Normal, family="Segoe UI") -> QFont:
        return QFont(family, self.font_size(base), int(weight))

    def bind(self, app: QApplication) -> None:
        self._app = app
        self._phibuilder = PhiBuilder(
            seed_color=_SEED_MAP.get(self._active, "#1565C0"),
            is_dark=_IS_DARK_MAP.get(self._active, False),
        )
        self._reapply()

    def _sync_phibuilder(self):
        if self._phibuilder is None:
            return
        self._phibuilder.set_seed_color(_SEED_MAP.get(self._active, "#1565C0"))
        self._phibuilder.set_dark_mode(_IS_DARK_MAP.get(self._active, False))

    def _reapply(self):
        if self._app is None:
            return
        combined = ""
        if self._phibuilder is not None:
            combined += self._phibuilder.qss + "\n"
        combined += self._generate_global_qss()
        self._app.setStyleSheet(combined)

    def _generate_global_qss(self) -> str:
        _ds = _get_ds()
        p = self._theme.palette
        f = self._theme.fonts
        s = self.font_size
        d = self._theme.design
        return f"""
            QToolTip {{
                background: {p.surface_variant}; color: {p.text_strong};
                border: 1px solid {p.outline}; padding: {_ds.space_xxs}px;  /* 4px Fibo padding */
                font-size: {s(f.small)}px;
            }}
            QMenu {{
                background: {p.surface}; color: {p.text_strong};
                border: 1px solid {p.outline};
                font-size: {s(f.base)}px;
            }}
            QMenu::item:selected {{
                background: {p.primary_container}; color: {p.text_strong};
            }}
            QScrollBar:vertical {{
                background: {p.surface_variant}; width: 8px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {p.outline}; border-radius: {_ds.radius_xs}px; min-height: {_ds.space_lg - _ds.space_xxs // 2}px;  /* 30px */
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            {QssHelper.table(p, d, s)}
        """


# ─── Sous-système P : Couleurs des programmes (PEI, MYP, DP, DPEn) ────────
# Les valeurs sont des noms de RÔLES (pas des couleurs) qui sont résolus
# dynamiquement depuis la palette active au moment de l'utilisation.
# Usage : PROGRAM_STYLES["PEI"] → ("primary", "primary_container", "on_primary")
# Chaque tuple = (rôle_fg, rôle_bg, rôle_on_fg)
PROGRAM_STYLES: dict[str, tuple[str, str, str]] = {
    "PYP":  ("primary",              "primary_container",         "on_primary"),
    "PP":   ("secondary",            "secondary_container",       "on_secondary"),
    "PEI":  ("primary",              "primary_container",         "on_primary"),
    "MYP":  ("secondary",            "secondary_container",       "on_secondary"),
    "DPFr": ("error",                "error_container",           "on_error"),
    "DPEn": ("tertiary",             "tertiary_container",        "on_tertiary"),
}

# Cache lazy pour ds (évite l'import circulaire theme.py ↔ design_system.py)
_ds_cache = None
def _get_ds():
    global _ds_cache
    if _ds_cache is None:
        from bladocommon.design_system import ds
        _ds_cache = ds
    return _ds_cache


class QssHelper:
    """Shared QSS fragment generators — single source of truth for both apps.

    Usage: p = theme_manager.palette; d = theme_manager.design; s = theme_manager.font_size
    Note: radius tokens uses ds.radius_* (M3 shapes), spacing uses ds.space_* (Fibo+M3)
    """

    @staticmethod
    def top_bar(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QFrame#top_bar {{ background: {p.surface}; color: {p.text_strong}; "
            f"border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_sm}px; }}"  # shape-small (8px) — Card-like
        )

    @staticmethod
    def panel(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QFrame#panel {{ background: {p.surface}; color: {p.text_strong}; "
            f"border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_sm}px; }}"  # shape-small (8px) — Card
        )

    @staticmethod
    def panel_title(p, s, fs) -> str:
        return (
            f"QLabel#panel_title {{ color: {p.text_strong}; "
            f"font-size: {s(fs)}px; font-weight: bold; }}"
        )

    @staticmethod
    def push_button(p, d, s) -> str:
        _ds = _get_ds()
        return (
            f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; border: none; "
            f"border-radius: {_ds.radius_lg}px; padding: {d.btn_pad_v}px {d.btn_pad_h}px; "  # shape-large (16px) — Filled Button
            f"font-size: {s(13)}px; }}"  # label-large (13px) — M3
            f"QPushButton:hover {{ background: {p.primary_container}; border-color: {p.primary}; }}"
            f"QPushButton:pressed {{ background: {p.primary}; color: {p.on_primary}; }}"
        )

    @staticmethod
    def table(p, d, s) -> str:
        _ds = _get_ds()
        return (
            f"QTableWidget {{ background: {p.surface}; color: {p.text_strong}; "
            f"border: none; gridline-color: {p.outline_variant}; "
            f"font-size: {s(12)}px; }}"
            f"QTableWidget::item {{ "
            f"background: {p.surface}; "  # Force le fond des cellules (contre le QSS phibuilder)
            f"color: {p.text_strong}; "
            f"padding: {d.btn_sm_pad_v}px {_ds.space_xs}px; "
            f"border-bottom: 1px solid {p.outline_variant}; }}"  # Row separator + text color + bg
            f"QTableWidget::item:selected {{ "
            f"background: {p.primary_container}; color: {p.text_strong}; }}"  # Selected row
            f"QTableWidget::item:hover {{ "
            f"background: {p.primary_container}; }}"  # Hover row
            f"QHeaderView::section {{ "
            f"background: {p.surface_variant}; color: {p.text_strong}; "
            f"padding: {d.btn_sm_pad_v}px {_ds.space_xs}px; "
            f"font-weight: bold; border: none; "
            f"border-bottom: 2px solid {p.outline}; }}"  # Header separator
        )

    @staticmethod
    def combobox(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QComboBox {{ background: {p.surface}; color: {p.text_strong}; "
            f"border: 1px solid {p.outline_variant}; border-radius: {_ds.radius_xs}px; "  # shape-extra-small (4px) — input-like
            f"padding: {d.field_pad_v}px {d.field_pad_h}px; }}"
            f"QComboBox:hover {{ border-color: {p.primary}; }}"
            f"QComboBox::drop-down {{ border: none; width: 20px; }}"
        )

    @staticmethod
    def period_btn(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QPushButton#period_btn {{ min-width: {theme_manager.image.logo}px; max-width: {theme_manager.image.logo}px; height: {theme_manager.image.theme_btn}px; "
            f"font-size: {theme_manager.font_size(13)}px; font-weight: normal; "
            f"border: {d.btn_border * 2}px solid transparent; border-radius: {_ds.radius_lg}px; "  # shape-large (16px) — button
            f"padding: 0; background: {p.surface_variant}; color: {p.text_strong}; }}"
            f"QPushButton#period_btn:hover {{ background: {p.primary_container}; "
            f"border-color: {p.primary}; }}"
            f"QPushButton#period_btn:checked {{ background: {p.primary}; color: {p.on_primary}; "
            f"border: {d.btn_border * 2}px solid {p.primary}; font-weight: bold; }}"
        )

    @staticmethod
    def input_field(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QLineEdit, QTextEdit, QPlainTextEdit {{ background: {p.surface}; "
            f"color: {p.text_strong}; border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_xs}px; padding: {d.field_pad_v}px {d.field_pad_h}px; }}"  # shape-extra-small (4px) — TextField
            f"QLineEdit:focus, QTextEdit:focus {{ border-color: {p.primary}; }}"
        )

    @staticmethod
    def kpi_common(p, d, s) -> str:
        _ds = _get_ds()
        return (
            f"QFrame#kpi_card {{ background: {p.surface}; border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_sm}px; padding: {_ds.space_xs}px; }}"  # shape-small (8px) — Card with border
            f"QLabel#kpi_value {{ font-size: {s(24)}px; font-weight: bold; color: {p.primary}; }}"
            f"QLabel#kpi_label {{ font-size: {s(10)}px; color: {p.text_strong}; }}"  # text_strong = lisibilité garantie dark comme light
            f"QFrame#kpi_small {{ background: {p.surface}; border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_sm}px; padding: {_ds.space_xxs}px; }}"  # Card with border
        )

    @staticmethod
    def sidebar_frame(p, d) -> str:
        return (
            f"QFrame#sidebar {{ background: {p.surface}; border: none; "
            f"border-right: 1px solid {p.outline_variant}; }}"
        )

    @staticmethod
    def phi_btn(p, d) -> str:
        _ds = _get_ds()
        return (
            f"QPushButton#phi_btn {{ font-size: {theme_manager.font_size(18)}px; border: 1px solid {p.outline_variant}; "
            f"border-radius: {_ds.radius_lg}px; background: {p.surface_variant}; color: {p.text_strong}; }}"  # shape-large (16px) — button
            f"QPushButton#phi_btn:checked {{ background: {p.primary}; color: {p.on_primary}; "
            f"border: {d.btn_border * 2}px solid {p.primary}; }}"
        )

    @staticmethod
    def section_btn(p, d, s) -> str:
        """Alias vers sidebar_section_header (même style flat divider)."""
        return QssHelper.sidebar_section_header(p, d, s)

    @staticmethod
    def class_btn(p, d, s) -> str:
        _ds = _get_ds()
        return (
            f"QPushButton#class_btn {{ border: none; border-radius: {_ds.radius_sm}px; "  # shape-small (8px) — compact button
            f"text-align: left; padding: {_ds.space_xxs}px {d.field_pad_h}px; "  # 4px vertical padding
            f"font-size: {s(10)}px; }}"
            f"QPushButton#class_btn:hover {{ background: {p.primary_container}; }}"
            f"QPushButton#class_btn:checked {{ font-weight: bold; }}"
        )

    @staticmethod
    def sidebar_section_header(p, d, s) -> str:
        """QSS avec sélecteur #sidebar_sec_hdr — pour usage dans _STYLE (parent).
        Fond surface_variant pour se démarquer du fond surface du sidebar."""
        _ds = _get_ds()
        return (
            f"#sidebar_sec_hdr {{ background: {p.surface_variant}; border: none; "
            f"border-bottom: 2px solid {p.outline_variant}; font-weight: bold; "
            f"font-size: {s(12)}px; color: {p.text_strong}; text-align: center; "
            f"padding: {_ds.space_xxs}px {_ds.space_xxs // 2}px; }}"
            f"#sidebar_sec_hdr:hover {{ color: {p.primary}; "
            f"border-bottom: 2px solid {p.primary}; }}"
        )

    @staticmethod
    def sidebar_section_header_inline(p, s) -> str:
        """QSS sans sélecteur — pour setStyleSheet() DIRECT sur le widget.
        Fond surface_variant pour se démarquer du fond surface du sidebar."""
        _ds = _get_ds()
        return (
            f"background: {p.surface_variant}; border: none; "
            f"border-bottom: 2px solid {p.outline_variant}; font-weight: bold; "
            f"font-size: {s(12)}px; color: {p.text_strong}; text-align: center; "
            f"padding: {_ds.space_xxs}px {_ds.space_xxs // 2}px;"
        )

    @staticmethod
    def sidebar_program_header(p, d, s, fg: str, bg: str, on_fg: str) -> str:
        """QSS avec sélecteur #sidebar_prog_hdr — pour usage dans _STYLE (parent)."""
        _ds = _get_ds()
        return (
            f"#sidebar_prog_hdr {{ background: {fg}; color: {on_fg}; border: none; "
            f"border-radius: {_ds.radius_sm}px; font-weight: bold; "
            f"font-size: {s(11)}px; padding: {_ds.space_xxs - _ds.space_xxs // 4}px; }}"
            f"#sidebar_prog_hdr:hover {{ background: {bg}; color: {fg}; }}"
        )

    @staticmethod
    def sidebar_program_header_inline(p, s, fg: str, on_fg: str) -> str:
        """QSS sans sélecteur — pour setStyleSheet() DIRECT sur le widget."""
        _ds = _get_ds()
        return (
            f"background: {fg}; color: {on_fg}; border: none; "
            f"border-radius: {_ds.radius_sm}px; font-weight: bold; "
            f"font-size: {s(11)}px; padding: {_ds.space_xxs - _ds.space_xxs // 4}px;"
        )

    @staticmethod
    def sidebar_class_button(p, d, s, bg: str, fg: str) -> str:
        """QSS avec sélecteur #sidebar_class_btn — pour usage dans _STYLE (parent)."""
        _ds = _get_ds()
        return (
            f"#sidebar_class_btn {{ background: {bg}; color: {fg}; border: none; "
            f"border-radius: {_ds.radius_sm}px; font-size: {s(11)}px; padding: {_ds.space_xxs // 2}px {_ds.space_xxs}px; }}"
            f"#sidebar_class_btn:hover {{ background: {fg}; color: {bg}; }}"
            f"#sidebar_class_btn:checked {{ background: {fg}; color: {bg}; "
            f"border: 2px solid {fg}; }}"
        )

    @staticmethod
    def sidebar_class_button_inline(p, s, bg: str, fg: str) -> str:
        """QSS sans sélecteur — pour setStyleSheet() DIRECT sur le widget."""
        _ds = _get_ds()
        return (
            f"background: {bg}; color: {fg}; border: none; "
            f"border-radius: {_ds.radius_sm}px; font-size: {s(11)}px; padding: {_ds.space_xxs // 2}px {_ds.space_xxs}px;"
        )

    @staticmethod
    def sidebar_all_button(p, d, s) -> str:
        """QSS avec sélecteur #sidebar_all_btn — pour usage dans _STYLE (parent)."""
        _ds = _get_ds()
        return (
            f"#sidebar_all_btn {{ background: {p.primary}; color: {p.on_primary}; "
            f"border: none; border-radius: {_ds.radius_lg}px; font-weight: bold; "
            f"font-size: {s(11)}px; padding: {_ds.space_xs}px; }}"
            f"#sidebar_all_btn:hover {{ background: {p.active}; }}"
        )

    @staticmethod
    def sidebar_all_button_inline(p, s) -> str:
        """QSS sans sélecteur — pour setStyleSheet() DIRECT sur le widget."""
        _ds = _get_ds()
        return (
            f"background: {p.primary}; color: {p.on_primary}; "
            f"border: none; border-radius: {_ds.radius_lg}px; font-weight: bold; "
            f"font-size: {s(11)}px; padding: {_ds.space_xs}px;"
        )

    @staticmethod
    def sidebar_container(p) -> str:
        """Conteneur du sidebar (frame ou scrollarea)."""
        return (
            f"QWidget#sidebar {{ background: {p.surface}; border: none; "
            f"border-right: 1px solid {p.outline_variant}; }}"
        )

    @staticmethod
    def login_qss(p) -> str:
        _ds = _get_ds()
        return f"""
            QWidget#root {{ background: {p.background}; }}
            QLabel {{ font-size: {theme_manager.font_size(13)}px; color: {p.text_strong}; background: transparent; }}
            QTabWidget::pane {{
                border: 1px solid {p.outline_variant}; background: {p.surface};
                border-radius: {_ds.radius_sm}px;
            }}
            QTabBar::tab          {{ padding: {_ds.space_xs}px {_ds.space_sm}px; font-size: {theme_manager.font_size(13)}px; }}
            QTabBar::tab:selected {{
                background: {p.surface}; border-bottom: 2px solid {p.primary};
                color: {p.text_strong}; font-weight: bold;
            }}
            QTabBar::tab:!selected {{ background: {p.surface_variant}; color: {p.text_strong}; }}
            QLineEdit {{
                padding: {_ds.space_xs}px {_ds.space_xs}px; border: 1px solid {p.outline_variant};
                border-radius: {_ds.radius_sm}px; font-size: {theme_manager.font_size(13)}px; background: {p.surface};
                color: {p.text_strong};
            }}
            QLineEdit:focus {{ border-color: {p.primary}; }}
            QPushButton {{
                padding: {_ds.space_xs}px {_ds.space_sm}px; border: none; border-radius: {_ds.radius_sm}px;
                font-size: {theme_manager.font_size(13)}px; font-weight: bold; color: white;
            }}
            QPushButton#btnIntra  {{ background: {p.primary}; }}
            QPushButton#btnIntra:hover  {{ background: {p.active}; }}
            QPushButton#btnIntra:disabled  {{ background: {p.inactive}; }}
            QPushButton#btnGoogle {{ background: #DB4437; }}
            QPushButton#btnGoogle:hover {{ background: #C53929; }}
            QPushButton#btnGoogle:disabled {{ background: {p.inactive}; }}
            QPushButton#btnCloud {{ background: {p.primary}; }}
            QPushButton#btnCloud:hover {{ background: {p.active}; }}
            QLabel#errLabel {{ color: {p.error}; font-size: {theme_manager.font_size(13)}px; }}
            QLabel#hdrTitle {{ color: {p.text_strong}; font-size: {theme_manager.font_size(21)}px; font-weight: bold; }}
            QLabel#hdrSub   {{ color: {p.text_soft}; font-size: {theme_manager.font_size(13)}px; }}
            QLabel#infoLbl  {{ color: {p.text_soft}; font-size: {theme_manager.font_size(13)}px; }}
            QLabel#formLbl {{ color: {p.text_strong}; font-size: {theme_manager.font_size(13)}px; }}
        """


theme_manager = ThemeManager()
