"""hr_charts — Widgets de visualisation RH en QPainter pur.

Zéro dépendance externe. Chaque widget est theme-reactive (connecté à
ds.theme_changed) et responsive (redessiné sur resizeEvent).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from bladocommon.design_system import ds
from bladocommon.icons import icon as md3_icon
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot

# Palette de couleurs pour segments (fallback si pas de couleur dans les données)
_SEGMENT_COLORS = ["#1565C0", "#2E7D32", "#FF8F00", "#C62828", "#6A1B9A",
                   "#00838F", "#4E342E", "#37474F", "#AD1457", "#283593"]


class HBarCell(QWidget):
    """Barre horizontale simple : [label] ████████████ N (XX%)."""

    def __init__(self, label: str = "", value: int = 0, total: int = 1,
                 color: str = "#1565C0", parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._total = max(total, 1)
        self._color = color
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumHeight(32)

    def set_data(self, label: str, value: int, total: int, color: str = ""):
        self._label = label
        self._value = value
        self._total = max(total, 1)
        if color:
            self._color = color
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        palette = theme_manager.palette
        w, h = self.width(), self.height()
        s = theme_manager.font_size

        # Fond
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(palette.surface))
        p.drawRoundedRect(1, 0, w - 2, h, ds.radius_xs, ds.radius_xs)

        ratio = self._value / self._total
        pct = int(round(ratio * 100))
        bar_h = ds.space_m3   # 16 px — barre épaisse (pas un trait fin)
        bar_y = (h - bar_h) // 2
        label_w = max(80, w // 4)
        bar_start = label_w + ds.space_xs
        bar_max_w = w - bar_start - 80

        # Label
        p.setPen(QColor(palette.text_strong))
        font = QFont()
        font.setPixelSize(s(12))
        p.setFont(font)
        p.drawText(QRectF(0, 0, label_w, h), Qt.AlignVCenter | Qt.AlignLeft,
                   self._label)

        # Barre fond — angles droits (une pilule arrondie ressemble à un bouton)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(palette.outline_variant))
        bg_rect = QRectF(bar_start, bar_y, bar_max_w, bar_h)
        p.drawRect(bg_rect)

        # Barre valeur — angles droits également
        if ratio > 0:
            bar_color = QColor(self._color)
            if not bar_color.isValid():
                bar_color = QColor(palette.primary)
            p.setBrush(bar_color)
            fill_w = max(bar_h, int(bar_max_w * ratio))
            fill_rect = QRectF(bar_start, bar_y, fill_w, bar_h)
            p.drawRect(fill_rect)

        # Valeur
        p.setPen(QColor(palette.text_soft))
        font.setPixelSize(s(11))
        p.setFont(font)
        val_text = f"{self._value} ({pct}%)"
        p.drawText(QRectF(bar_start + bar_max_w + ds.space_xxs, 0, 75, h),
                   Qt.AlignVCenter | Qt.AlignLeft, val_text)

        p.end()


class RingChart(QWidget):
    """Anneau/donut multicolore avec total au centre."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._segments: list[dict] = []  # [{label, value, color}, ...]
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(160, 160)

    def set_segments(self, segments: list[dict], title: str = ""):
        self._segments = segments
        if title:
            self._title = title
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        palette = theme_manager.palette
        s = theme_manager.font_size
        w, h = self.width(), self.height()

        # Fond
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(palette.surface))
        p.drawRoundedRect(1, 0, w - 2, h, ds.radius_sm, ds.radius_sm)

        total = sum(seg.get("value", 0) for seg in self._segments)
        if total == 0 or not self._segments:
            p.setPen(QColor(palette.text_soft))
            font = QFont()
            font.setPixelSize(s(12))
            p.setFont(font)
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "Aucune donnée")
            p.end()
            return

        # Dimensions de l'anneau
        ring_outer = min(w, h) * 0.35
        ring_inner = ring_outer * 0.55
        cx, cy = w / 2.0, h / 2.0
        ring_thickness = ring_outer - ring_inner

        # Dessiner les arcs
        angle_start = 90  # commencer en haut (12h)
        for i, seg in enumerate(self._segments):
            val = seg.get("value", 0)
            span = (val / total) * 360.0 * 16  # Qt utilise 1/16e de degré
            if span < 1:
                angle_start += span
                continue
            color = seg.get("color", _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)])
            pen = QPen(QColor(color), ring_thickness)
            pen.setCapStyle(Qt.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - ring_outer, cy - ring_outer,
                             ring_outer * 2, ring_outer * 2),
                      int(angle_start), int(span))
            angle_start += span

        # Cercle intérieur (masque pour effet donut)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(palette.surface))
        p.drawEllipse(QRectF(cx - ring_inner, cy - ring_inner,
                             ring_inner * 2, ring_inner * 2))

        # Texte central
        font_total = QFont()
        font_total.setPixelSize(s(22))
        font_total.setBold(True)
        p.setFont(font_total)
        p.setPen(QColor(palette.text_strong))
        p.drawText(QRectF(0, cy - ring_inner + 8, w, 28), Qt.AlignHCenter | Qt.AlignTop,
                   str(total))

        font_label = QFont()
        font_label.setPixelSize(s(10))
        p.setFont(font_label)
        p.setPen(QColor(palette.text_soft))
        p.drawText(QRectF(0, cy + 4, w, 20), Qt.AlignHCenter | Qt.AlignTop,
                   self._title)

        # Légende (sous l'anneau si assez de place, sinon à droite)
        legend_y = cy + ring_outer + ds.space_sm
        if legend_y + 20 * len(self._segments) < h:
            p.setFont(font_label)
            for i, seg in enumerate(self._segments):
                ly = legend_y + i * 18
                color = seg.get("color", _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)])
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(color))
                p.drawRoundedRect(QRectF(ds.space_md, ly, 10, 10), 2, 2)
                p.setPen(QColor(palette.text_soft))
                p.drawText(QRectF(ds.space_md + 16, ly - 2, w - ds.space_md - 20, 16),
                           Qt.AlignVCenter | Qt.AlignLeft,
                           f"{seg.get('label', '')}: {seg.get('value', 0)}")

        p.end()


class StatChange(QWidget):
    """Tuile statistique avec valeur + flèche de tendance + delta."""

    def __init__(self, label: str = "", value: str = "", delta: float = 0.0,
                 parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._delta = delta
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(140, 80)

    def set_data(self, label: str, value: str, delta: float = 0.0):
        self._label = label
        self._value = value
        self._delta = delta
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        palette = theme_manager.palette
        s = theme_manager.font_size
        w, h = self.width(), self.height()

        # Fond
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(palette.surface))
        p.drawRoundedRect(1, 0, w - 2, h, ds.radius_sm, ds.radius_sm)

        # Valeur principale
        font_val = QFont()
        font_val.setPixelSize(s(24))
        font_val.setBold(True)
        p.setFont(font_val)
        p.setPen(QColor(palette.text_strong))
        p.drawText(QRectF(ds.space_sm, ds.space_xs, w - ds.space_sm * 2, 32),
                   Qt.AlignLeft | Qt.AlignTop, self._value)

        # Label
        font_lbl = QFont()
        font_lbl.setPixelSize(s(10))
        p.setFont(font_lbl)
        p.setPen(QColor(palette.text_soft))
        p.drawText(QRectF(ds.space_sm, ds.space_xs + 30, w - ds.space_sm * 2, 18),
                   Qt.AlignLeft | Qt.AlignTop, self._label)

        # Delta
        if self._delta != 0:
            arrow = "▲" if self._delta > 0 else "▼"
            delta_color = QColor(palette.error) if self._delta > 0 else QColor(palette.success)
            # En RH, une hausse d'absentéisme (▲) est négative → error
            # Pour les widgets génériques, on laisse l'appelant décider
            delta_text = f"{arrow} {abs(self._delta):.1f}%"
            p.setPen(delta_color)
            font_delta = QFont()
            font_delta.setPixelSize(s(11))
            font_delta.setBold(True)
            p.setFont(font_delta)
            p.drawText(QRectF(ds.space_sm, h - 24, w - ds.space_sm * 2, 20),
                       Qt.AlignLeft | Qt.AlignBottom, delta_text)

        p.end()


class AlertRow(QWidget):
    """Ligne d'alerte : icône + message + compteur, fond coloré.

    Adapte automatiquement sa couleur : error (count > 0) ou success (count == 0).
    """

    def __init__(self, icon_name: str = "warning", text: str = "",
                 count: int = 0, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._text = text
        self._count = count
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumHeight(44)

    def set_data(self, icon_name: str, text: str, count: int):
        self._icon_name = icon_name
        self._text = text
        self._count = count
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        palette = theme_manager.palette
        s = theme_manager.font_size
        w, h = self.width(), self.height()

        # Couleurs selon état
        is_alert = self._count > 0
        bg_color = QColor(palette.error_container if is_alert else palette.success)
        fg_color = QColor(palette.error if is_alert else palette.on_primary)

        bg_color.setAlpha(40 if not is_alert else 255)
        p.setPen(Qt.NoPen)
        p.setBrush(bg_color)
        p.drawRoundedRect(0, 0, w, h, ds.radius_sm, ds.radius_sm)

        # Icône
        icon_x = ds.space_sm
        icon_size = 20
        icon_y = (h - icon_size) // 2

        if is_alert:
            p.setPen(QColor(palette.error))
            p.setBrush(QColor(palette.error))
            path = QPainterPath()
            path.moveTo(icon_x + icon_size // 2, icon_y)
            path.lineTo(icon_x + icon_size, icon_y + icon_size)
            path.lineTo(icon_x, icon_y + icon_size)
            path.closeSubpath()
            p.drawPath(path)
            p.setPen(QColor(palette.on_error))
            p.setBrush(QColor(palette.on_error))
            p.drawRect(icon_x + icon_size // 2 - 1, icon_y + 7, 2, 6)
            p.drawRect(icon_x + icon_size // 2 - 1, icon_y + 14, 2, 2)
        else:
            # Cercle vert check
            p.setPen(QColor(palette.success))
            p.setBrush(QColor(palette.success))
            p.drawEllipse(icon_x + 2, icon_y + 2, icon_size - 4, icon_size - 4)
            p.setPen(QColor(palette.on_primary))
            p.drawLine(icon_x + 6, icon_y + icon_size // 2,
                       icon_x + icon_size // 2, icon_y + icon_size - 4)
            p.drawLine(icon_x + icon_size // 2, icon_y + icon_size - 4,
                       icon_x + icon_size - 2, icon_y + 4)

        # Texte
        p.setPen(QColor(palette.text_strong))
        font = QFont()
        font.setPixelSize(s(12))
        p.setFont(font)
        text_x = icon_x + icon_size + ds.space_sm
        p.drawText(QRectF(text_x, 0, w - text_x - 60, h),
                   Qt.AlignVCenter | Qt.AlignLeft, self._text)

        # Compteur badge
        if is_alert:
            p.setPen(QColor(palette.error))
            font_badge = QFont()
            font_badge.setPixelSize(s(14))
            font_badge.setBold(True)
            p.setFont(font_badge)
            p.drawText(QRectF(w - 50, 0, 42, h), Qt.AlignVCenter | Qt.AlignRight,
                       str(self._count))

        p.end()
