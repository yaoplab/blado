"""M3DateEdit — wrapper phibuilder pour QDateEdit."""
from PySide6.QtWidgets import QDateEdit
from PySide6.QtCore import QDate
from phibuilder.theme import Theme
from phibuilder.phi.scale import SpacingToken


class M3DateEdit(QDateEdit):
    def __init__(self, date=None, theme: Theme | None = None, parent=None):
        super().__init__(date or QDate.currentDate(), parent)
        self._theme = theme
        self.setCalendarPopup(True)
        self.setDisplayFormat("dddd dd MMMM yyyy")
        self._update_style()

    def _update_style(self):
        if self._theme is None:
            return
        c, s = self._theme.colors, self._theme.spacing
        # height 27 → rendu 32 px (QDateEdit rend height + 5 : bordure + boutons spin)
        self.setStyleSheet(
            f"M3DateEdit {{ padding: 0 {s.spacing(SpacingToken.MD)}px; border: 1px solid {c.outline_variant}; "
            f"border-radius: {s.spacing(SpacingToken.XXS)}px; font-size: {s.spacing(SpacingToken.XL) // 4}px; "  # 13px — pas de token typo M3 exact
            f"background: {c.surface}; color: {c.on_surface}; font-weight: bold; "
            f"height: {s.spacing(SpacingToken.LG) - s.spacing(SpacingToken.XXS) // 2 - 3}px; }}"
        )
