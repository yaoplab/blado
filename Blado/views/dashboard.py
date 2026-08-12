"""HRDashboard — Tableau de bord RH responsive (métallurgie)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea,
    QSizePolicy,
)

from bladocommon.design_system import ds
from bladocommon.icons import icon as md3_icon
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot

from Blado.common.blado_database import BladoDatabase
from Blado.views.charts import HBarCell, RingChart, StatChange, AlertRow, _SEGMENT_COLORS


class _KpiCard(QFrame):
    """Carte KPI responsive avec barre d'accent + icône + valeur + label."""

    def __init__(self, label: str, accent_token: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self._label_text = label
        self._accent_token = accent_token
        self._icon_name = icon_name
        self._value = "—"
        self._value_label: QLabel | None = None
        self.setObjectName("kpi_card")
        self.setMinimumWidth(ds.kpi_card_min_width)
        self.setFixedHeight(ds.kpi_card_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._setup_ui()
        ds.theme_changed.connect(self._restyle)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(ds.space_md, ds.space_sm, ds.space_md, ds.space_sm)
        layout.setSpacing(ds.space_sm)

        bar = QWidget()
        bar.setObjectName("accent")
        bar.setFixedWidth(ds.space_xxs)
        layout.addWidget(bar)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(ds.icon_md, ds.icon_md)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("border: none;")
        self._icon_label = icon_lbl
        layout.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(0)
        self._value_label = QLabel(self._value)
        col.addWidget(self._value_label)
        lbl = QLabel(self._label_text)
        col.addWidget(lbl)
        layout.addLayout(col, 1)
        self._restyle()

    def set_value(self, value: str):
        self._value = value
        if self._value_label:
            self._value_label.setText(value)

    @safe_slot("_KpiCard._restyle")
    def _restyle(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        accent = getattr(p, self._accent_token, p.primary)
        self.setStyleSheet(f"""
            #kpi_card {{
                background: {p.surface}; border: 1px solid {p.outline_variant};
                border-radius: {ds.radius_sm}px;
            }}
            QWidget#accent {{ background: {accent}; border-radius: {int(ds.radius_xs/2)}px; }}
        """)
        if self._value_label:
            self._value_label.setStyleSheet(
                f"font-size: {s(ds.font_h2)}px; font-weight: bold; color: {accent}; border: none;")
        for lbl in self.findChildren(QLabel):
            if lbl is not self._value_label and lbl is not self._icon_label:
                lbl.setStyleSheet(
                    f"font-size: {s(ds.font_small)}px; color: {p.text_soft}; border: none;")
        if self._icon_label and self._icon_name:
            self._icon_label.setPixmap(
                md3_icon(self._icon_name, color=accent, size=ds.icon_sm).pixmap(ds.icon_sm, ds.icon_sm))


class _SectionCard(QFrame):
    """Carte conteneur avec titre + séparateur + contenu."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("section_card")
        self._title = title
        self._setup_ui()
        ds.theme_changed.connect(self._restyle)

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(ds.space_md, ds.space_sm, ds.space_md, ds.space_md)
        self._layout.setSpacing(ds.space_sm)

        self._title_label = QLabel(self._title)
        self._layout.addWidget(self._title_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sep")
        self._layout.addWidget(sep)

        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(ds.space_xxs)
        self._layout.addLayout(self._content_layout, 1)
        self._restyle()

    def content_layout(self):
        return self._content_layout

    @safe_slot("_SectionCard._restyle")
    def _restyle(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        self.setStyleSheet(f"""
            #section_card {{
                background: {p.surface}; border: 1px solid {p.outline_variant};
                border-radius: {ds.radius_sm}px;
            }}
            QFrame#sep {{ color: {p.outline_variant}; border: none; max-height: 1px; }}
        """)
        self._title_label.setStyleSheet(
            f"font-size: {s(ds.font_title)}px; font-weight: bold; color: {p.text_strong}; border: none;")


class HRDashboard(QScrollArea):
    """Tableau de bord RH responsive — métallurgie."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setObjectName("hr_dashboard")

        self._container = QWidget()
        self._container.setObjectName("dashboard_container")
        self._container.installEventFilter(self)
        self.setWidget(self._container)

        self._root_layout = QVBoxLayout(self._container)
        self._root_layout.setContentsMargins(ds.space_md, ds.space_md, ds.space_md, ds.space_md)
        self._root_layout.setSpacing(ds.space_md)

        ds.theme_changed.connect(self._restyle)
        self._setup_ui()

    def _STYLE(self) -> str:
        p = theme_manager.palette
        return (f"#hr_dashboard {{ background: {p.background}; border: none; }}"
                f"#dashboard_container {{ background: {p.background}; }}")

    @safe_slot("HRDashboard._restyle")
    def _restyle(self):
        try:
            self.setStyleSheet(self._STYLE())
            p = theme_manager.palette
            s = theme_manager.font_size
            if hasattr(self, "_title_label"):
                self._title_label.setStyleSheet(
                    f"font-size: {s(ds.font_h1)}px; font-weight: bold; "
                    f"color: {p.text_strong}; border: none;")
        except RuntimeError:
            pass

    def eventFilter(self, obj, event):
        if obj is self._container and event.type() == QEvent.Resize:
            self._relayout_kpis()
        return super().eventFilter(obj, event)

    def _setup_ui(self):
        # ── Titre ──
        self._title_label = QLabel("Tableau de bord RH — Métallurgie")
        self._title_label.setObjectName("dashboard_title")
        self._root_layout.addWidget(self._title_label)

        # ── KPIs responsive ──
        self._kpi_grid = QGridLayout()
        self._kpi_grid.setSpacing(ds.space_sm)
        self._root_layout.addLayout(self._kpi_grid)

        self._kpi_cards: dict[str, _KpiCard] = {
            "effectif": _KpiCard("Effectif actif", "primary", "group"),
            "contrats": _KpiCard("Contrats actifs", "success", "contract"),
            "absents":   _KpiCard("Absents du jour", "error", "event"),
            "conges":    _KpiCard("Congés en attente", "secondary", "schedule"),
            "expirant":  _KpiCard("Contrats < 30 j", "tertiary", "warning"),
        }
        self._relayout_kpis()

        # ── Rangée 1 : Services + Contrats ──
        row1 = QHBoxLayout()
        row1.setSpacing(ds.space_sm)

        svc_card = _SectionCard("Effectif par service")
        svc_card.content_layout().addStretch()
        row1.addWidget(svc_card, 6)
        self._svc_section = svc_card

        ctr_card = _SectionCard("Contrats par type")
        self._contract_ring = RingChart("contrats")
        ctr_card.content_layout().addWidget(self._contract_ring)
        row1.addWidget(ctr_card, 4)
        self._root_layout.addLayout(row1)

        # ── Rangée 2 : Absentéisme + Tâches ──
        row2 = QHBoxLayout()
        row2.setSpacing(ds.space_sm)

        self._absence_stat = StatChange("Taux d'absentéisme 30j", "—", 0.0)
        row2.addWidget(self._absence_stat, 1)

        self._tasks_alert = AlertRow("error", "Tâches en retard", 0)
        row2.addWidget(self._tasks_alert, 1)
        self._root_layout.addLayout(row2)

        # ── Rangée 3 : Complétude ──
        cmp_card = _SectionCard("Complétude des dossiers")
        self._cmp_pct    = _KpiCard("Dossiers complets", "success", "check_circle")
        self._cmp_miss   = _KpiCard("Dossiers incomplets", "error", "error")
        self._cmp_id     = _KpiCard("Pièces ID expirées", "error", "warning")
        self._cmp_trial  = _KpiCard("Périodes d'essai", "tertiary", "timeline")

        cgrid = QGridLayout()
        cgrid.setSpacing(ds.space_sm)
        cgrid.addWidget(self._cmp_pct, 0, 0)
        cgrid.addWidget(self._cmp_miss, 0, 1)
        cgrid.addWidget(self._cmp_id, 0, 2)
        cgrid.addWidget(self._cmp_trial, 0, 3)
        cmp_card.content_layout().addLayout(cgrid)

        self._missing_bars_layout = QVBoxLayout()
        self._missing_bars_layout.setSpacing(ds.space_xxs)
        cmp_card.content_layout().addLayout(self._missing_bars_layout)

        self._docs_bars_layout = QVBoxLayout()
        self._docs_bars_layout.setSpacing(ds.space_xxs)
        cmp_card.content_layout().addLayout(self._docs_bars_layout)

        self._root_layout.addWidget(cmp_card)
        self._completeness_section = cmp_card

        self._root_layout.addStretch(1)
        self._restyle()
        self.refresh()

    def _relayout_kpis(self):
        """Grille KPI responsive : s'adapte à la largeur disponible."""
        try:
            for i in range(self._kpi_grid.count() - 1, -1, -1):
                item = self._kpi_grid.itemAt(i)
                if item and item.widget():
                    self._kpi_grid.removeWidget(item.widget())
        except RuntimeError:
            return  # widget déjà détruit

        w = max(self._container.width() - ds.space_md * 2, 400)
        cols = max(1, min(5, w // (ds.kpi_card_min_width + ds.space_sm)))
        for i, (key, card) in enumerate(self._kpi_cards.items()):
            row, col = divmod(i, cols)
            self._kpi_grid.addWidget(card, row, col)

    # ════════════════════════════════════════════════════════════════
    # Refresh
    # ════════════════════════════════════════════════════════════════

    def refresh(self):
        kpis = BladoDatabase.get_dashboard_kpis()

        def _v(key, default="—"):
            val = kpis.get(key, 0) if kpis else 0
            return "—" if val == -1 else str(val)

        self._kpi_cards["effectif"].set_value(_v("total_active"))
        self._kpi_cards["contrats"].set_value(_v("active_contracts"))
        self._kpi_cards["absents"].set_value(_v("absent_today"))
        self._kpi_cards["conges"].set_value(_v("pending_leave"))
        self._kpi_cards["expirant"].set_value(_v("expiring_contracts"))

        self._refresh_services()
        self._refresh_contracts()
        self._refresh_absence()
        self._refresh_tasks()
        self._refresh_completeness()
        self._relayout_kpis()

    def _clear_layout(self, layout):
        """Vide un layout en supprimant ses widgets, avec garde RuntimeError."""
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                layout.removeWidget(w)
                try:
                    w.deleteLater()
                except RuntimeError:
                    pass

    def _refresh_services(self):
        cl = self._svc_section.content_layout()
        self._clear_layout(cl)

        services = BladoDatabase.get_headcount_by_service()
        if not services:
            empty = QLabel("Aucune donnée")
            empty.setStyleSheet(f"color: {theme_manager.palette.text_soft}; "
                               f"font-size: {theme_manager.font_size(ds.font_small)}px; border: none;")
            empty.setAlignment(Qt.AlignCenter)
            cl.addWidget(empty)
            return
        total = sum(c["count"] for c in services)
        for c in services:
            cl.addWidget(HBarCell(c["label"], c["count"], total, c.get("color", "")))

    def _refresh_contracts(self):
        contracts = BladoDatabase.get_contracts_by_type()
        if not contracts:
            self._contract_ring.set_segments([], "")
            return
        segments = []
        for i, ct in enumerate(contracts):
            segments.append({
                "label": ct.get("type", "?"),
                "value": ct["count"],
                "color": _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)],
            })
        self._contract_ring.set_segments(segments, f"{sum(c['count'] for c in contracts)} contrats")

    def _refresh_absence(self):
        absence = BladoDatabase.get_absence_rate_30d()
        if absence:
            self._absence_stat.set_data(
                f"{absence.get('rate', 0)}%  ·  {absence.get('total_events', 0)} événements",
                f"{absence.get('days_with_absence', 0)} jours/30",
                absence.get("delta", 0))

    def _refresh_tasks(self):
        overdue = BladoDatabase.get_overdue_tasks()
        if overdue > 0:
            self._tasks_alert.set_data("error",
                f"{overdue} tâche(s) en retard — échéance dépassée", overdue)
        else:
            self._tasks_alert.set_data("check_circle", "Aucune tâche en retard", 0)

    def _refresh_completeness(self):
        try:
            completeness = BladoDatabase.get_completeness_stats()
            self._cmp_pct.set_value(f"{completeness['pct']}%")
            self._cmp_miss.set_value(str(completeness['incomplete']))
            self._cmp_id.set_value(str(BladoDatabase.get_expiring_id_docs()))
            self._cmp_trial.set_value(str(BladoDatabase.get_trial_periods_ending()))

            self._clear_layout(self._missing_bars_layout)
            for m in BladoDatabase.get_missing_fields_stats():
                self._missing_bars_layout.addWidget(
                    HBarCell(m['label'], m['missing'], completeness['total'], theme_manager.palette.error))

            self._clear_layout(self._docs_bars_layout)
            for d in BladoDatabase.get_missing_docs_stats():
                self._docs_bars_layout.addWidget(
                    HBarCell(d['label'], d['missing'], completeness['total'], theme_manager.palette.tertiary))
        except RuntimeError:
            pass  # widget déjà détruit — normal pendant un redraw rapide

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self._relayout_kpis()
        except RuntimeError:
            pass
