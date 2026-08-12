from PySide6.QtWidgets import QComboBox, QSizePolicy
from phibuilder.theme import Theme
from phibuilder.phi.scale import PhiScale, SpacingToken

# Échelle phi partagée (base 4) pour les tailles indépendantes du thème
_SCALE = PhiScale()

class M3ComboBox(QComboBox):
    def __init__(self, items: list[str] | None = None, theme: Theme | None = None, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(_SCALE.spacing(SpacingToken.MD) * 2)  # 40px
        if items:
            self.addItems(items)
        self._update_style()
    def _update_style(self):
        if self._theme is None:
            return
        t, c, s = self._theme, self._theme.colors, self._theme.spacing
        p, r = s.spacing(SpacingToken.MD), s.spacing(SpacingToken.XS)
        self.setStyleSheet(f"""
M3ComboBox {{ padding: 0 {p}px; height: {p * 2}px; border: 1px solid {c.outline}; border-radius: {r}px;
  background-color: {c.surface}; color: {c.on_surface}; font-family: '{t.typo.family}'; font-size: {t.typo.body_large.size}px; }}
M3ComboBox:hover {{ border-color: {c.on_surface}; }}
M3ComboBox:focus, M3ComboBox:open {{ border: 2px solid {c.primary}; }}
M3ComboBox::drop-down {{ border: none; width: {s.spacing(SpacingToken.XXL)}px; }}
M3ComboBox::down-arrow {{ width: {s.spacing(SpacingToken.MD)}px; height: {s.spacing(SpacingToken.MD)}px; }}
M3ComboBox QAbstractItemView {{ background-color: {c.surface}; border: 1px solid {c.outline}; border-radius: {r}px;
  padding: {s.spacing(SpacingToken.XS)}px; outline: none; color: {c.on_surface};
  font-family: '{t.typo.family}'; font-size: {t.typo.body_medium.size}px;
  selection-background-color: {c.primary_container}; selection-color: {c.on_primary_container}; }}
M3ComboBox QAbstractItemView::item {{ padding: {s.spacing(SpacingToken.SM)}px {s.spacing(SpacingToken.MD)}px;
  border-radius: {s.spacing(SpacingToken.XS)}px; min-height: {s.spacing(SpacingToken.XL)}px; }}
""")
