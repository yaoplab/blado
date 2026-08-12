"""M3ScrollArea — wrapper phibuilder pour QScrollArea."""
from PySide6.QtWidgets import QScrollArea
from phibuilder.theme import Theme


class M3ScrollArea(QScrollArea):
    def __init__(self, theme: Theme | None = None, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setWidgetResizable(True)
        self._update_style()

    def _update_style(self):
        if self._theme is None:
            return
        c = self._theme.colors
        self.setStyleSheet(
            f"M3ScrollArea {{ background: {c.surface}; border: none; }}"
            f"M3ScrollArea::viewport {{ background: {c.surface}; }}"
        )
