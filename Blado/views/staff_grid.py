"""StaffGrid — grille photos responsive (QScrollArea + QGridLayout adaptatif)."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSizePolicy, QComboBox, QFileDialog,
)

from phibuilder.widgets.table import M3TableWidget
from phibuilder.widgets.scrollarea import M3ScrollArea

from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.icons import icon as md3_icon
from bladocommon.safe_slot import safe_slot

# Card grid pattern — exactement selon le skill
CARD_W = ds.space_xxxl          # 136
CARD_H = ds.space_xxxl * 2      # 272
SPACING = ds.space_xs           # 8
MARGIN = ds.space_xs            # 8

_STATUS_LABELS = {
    "actif": "Actif", "suspendu": "Suspendu",
    "en_préavis": "En préavis", "parti": "Parti",
}


def _find_photo(staff_id: int) -> str:
    """Cherche la photo du staff dans Blado puis LarcSuperviseur.

    Retourne le chemin complet ou une chaîne vide si aucune trouvée.
    """
    base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [
        os.path.join(base, "Blado", "photos", f"{staff_id}.png"),
        os.path.join(base, "LarcSuperviseur", "photos", f"{staff_id}.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""


def _make_avatar(name: str, size: int = 100) -> QPixmap:
    """Avatar à initiales avec couleur déterministe (stable entre sessions)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    hue = sum(ord(c) for c in (name or "?")) % 360
    p.setBrush(QColor.fromHsl(hue, 160, 120))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, size // 4, size // 4)
    initials = "".join(part[0].upper() for part in (name or "?").split()[:2]) or "?"
    p.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", size // 3, QFont.Bold)
    p.setFont(font)
    p.drawText(0, 0, size, size, Qt.AlignCenter, initials)
    p.end()
    return pix


class _StaffCard(QFrame):

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("staff_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(CARD_W)
        self.setFixedHeight(CARD_H)
        self._status_lbl: QLabel | None = None
        self._styled_labels: list[QLabel] = []
        self.setStyleSheet(self._style())
        self._setup_ui()
        ds.theme_changed.connect(self._restyle)

    def _style(self) -> str:
        p = theme_manager.palette
        return f"""
            #staff_card {{
                background: {p.surface}; border: 1px solid {p.outline_variant};
                border-radius: {ds.radius_sm}px;
            }}
            #staff_card:hover {{ border-color: {p.primary}; }}
        """

    def _setup_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(ds.space_xs, ds.space_xs, ds.space_xs, ds.space_xs)
        layout.setSpacing(3)

        # Photo
        photo_path = _find_photo(self._data.get("id", 0))
        photo_lbl = QLabel()
        photo_lbl.setFixedSize(ds.space_xxl, ds.space_xxl)
        photo_lbl.setAlignment(Qt.AlignCenter)
        pix = None
        if photo_path:
            pix = QPixmap(photo_path).scaled(ds.space_xxl, ds.space_xxl,
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if pix is None or pix.isNull():
            pix = _make_avatar(self._data.get("full_name", ""), ds.space_xxl)
        photo_lbl.setPixmap(pix)
        photo_lbl.setStyleSheet(
            f"QLabel {{ border-radius: {ds.space_xxl // 2}px; background: transparent; }}")
        layout.addWidget(photo_lbl, 0, Qt.AlignCenter)

        # Nom
        self._name_lbl = QLabel(self._data.get("full_name", "—"))
        self._name_lbl.setAlignment(Qt.AlignCenter)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet(
            f"font-size: {s(12)}px; font-weight: bold; color: {p.text_strong}; border: none;")
        layout.addWidget(self._name_lbl)
        self._styled_labels.append(self._name_lbl)

        # Fonction
        fonction = self._data.get("professional_category", "") or ""
        if fonction:
            self._role_lbl = QLabel(fonction)
            self._role_lbl.setAlignment(Qt.AlignCenter)
            self._role_lbl.setStyleSheet(
                f"font-size: {s(10)}px; color: {p.primary}; border: none;")
            layout.addWidget(self._role_lbl)
            self._styled_labels.append(self._role_lbl)
        else:
            self._role_lbl = None

        # Catégorie professionnelle
        pro_cat = self._data.get("professional_category", "") or ""
        if pro_cat:
            self._cat_lbl = QLabel(pro_cat)
            self._cat_lbl.setAlignment(Qt.AlignCenter)
            self._cat_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
            layout.addWidget(self._cat_lbl)
            self._styled_labels.append(self._cat_lbl)
        else:
            self._cat_lbl = None

        # Matricule
        matricule = self._data.get("matricule", "") or ""
        if matricule:
            self._mat_lbl = QLabel(matricule)
            self._mat_lbl.setAlignment(Qt.AlignCenter)
            self._mat_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
            layout.addWidget(self._mat_lbl)
            self._styled_labels.append(self._mat_lbl)
        else:
            self._mat_lbl = None

        # Statut (badge coloré)
        status = (self._data.get("emp_status") or "actif").lower()
        status_label = _STATUS_LABELS.get(status, status.title())
        status_colors = {
            "actif": (p.success, p.success),
            "suspendu": (p.tertiary, p.tertiary),
            "en_préavis": (p.tertiary, p.tertiary),
            "parti": (p.error, p.error),
        }
        sc_bg, sc_fg = status_colors.get(status, (p.outline_variant, p.text_soft))
        self._status_lbl = QLabel(f" ● {status_label}")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"font-size: {s(9)}px; font-weight: bold; color: {sc_fg}; "
            f"background: transparent; border: none; padding: 1px 0px;")
        layout.addWidget(self._status_lbl)

        # Service
        service_label = self._data.get("service_label", "") or ""
        if service_label:
            self._Service_lbl = QLabel(service_label)
            self._Service_lbl.setAlignment(Qt.AlignCenter)
            self._Service_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
            layout.addWidget(self._Service_lbl)
            self._styled_labels.append(self._Service_lbl)
        else:
            self._Service_lbl = None

        layout.addStretch()

        # Bouton événement
        btn_row = QHBoxLayout()
        btn_row.setSpacing(ds.space_xs)
        btn_row.addStretch()
        event_btn = QPushButton()
        event_btn.setIcon(md3_icon("event", color=p.primary, size=16))
        event_btn.setFixedSize(ds.space_lg, ds.space_lg)
        event_btn.setCursor(Qt.PointingHandCursor)
        event_btn.setToolTip("Événements")
        event_btn.clicked.connect(lambda: self._on_event())
        event_btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {p.outline}; border-radius: "
            f"{ds.radius_xs}px; background: transparent; }} "
            f"QPushButton:hover {{ background: {p.surface_variant}; }}")
        btn_row.addWidget(event_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    @safe_slot("_StaffCard._on_event")
    def _on_event(self):
        from Blado.views.staff_events import open_staff_event_generator
        open_staff_event_generator(self._data, self)

    @safe_slot("_StaffCard._restyle")
    def _restyle(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        self.setStyleSheet(self._style())
        # Nom
        self._name_lbl.setStyleSheet(
            f"font-size: {s(12)}px; font-weight: bold; color: {p.text_strong}; border: none;")
        # Rôle
        if self._role_lbl:
            self._role_lbl.setStyleSheet(
                f"font-size: {s(10)}px; color: {p.primary}; border: none;")
        # Catégorie pro
        if self._cat_lbl:
            self._cat_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
        # Matricule
        if self._mat_lbl:
            self._mat_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
        # Service
        if self._Service_lbl:
            self._Service_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
        # Statut
        if self._status_lbl:
            status = (self._data.get("emp_status") or "actif").lower()
            status_colors = {
                "actif": p.success, "suspendu": p.tertiary,
                "en_préavis": p.tertiary, "parti": p.error,
            }
            sc_fg = status_colors.get(status, p.text_soft)
            self._status_lbl.setStyleSheet(
                f"font-size: {s(9)}px; font-weight: bold; color: {sc_fg}; "
                f"background: transparent; border: none; padding: 1px 0px;")

    def mouseDoubleClickEvent(self, event):
        w = self.parent()
        while w:
            if isinstance(w, StaffGrid):
                w.staff_selected.emit(self._data)
                return
            w = w.parent()


class StaffGrid(QWidget):
    """Grille de photos responsive avec toolbar de recherche/filtres."""

    staff_selected = Signal(dict)

    def _show_detail(self, data: dict):
        self.staff_selected.emit(data)

    def __init__(self, cat_key: str, id_lo: int, id_hi: int,
                 is_staff: bool = False, parent=None):
        super().__init__(parent)
        self._cat_key = cat_key
        self._id_lo = id_lo
        self._id_hi = id_hi
        self._is_staff = is_staff
        self._cols = 1
        self._view_mode = "grid"  # "grid" or "table"
        self._search_text = ""
        self._filter_service: int | None = None
        self._filter_status: str | None = None
        self._sort_by = "name"
        self._all_data: list[dict] = []
        ds.theme_changed.connect(self.refresh)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Toolbar ──
        self._setup_toolbar(outer)

        # ── Scroll area for cards / table ──
        self._scroll = M3ScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background: {theme_manager.palette.background}; border: none;")

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        self._grid.setSpacing(SPACING)
        self._table_view: M3TableWidget | None = None

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

        self.refresh()

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    def _setup_toolbar(self, parent_layout):
        p = theme_manager.palette
        toolbar = QWidget()
        toolbar.setAttribute(Qt.WA_StyledBackground, True)
        toolbar.setStyleSheet(f"background: {p.surface}; border-bottom: 1px solid {p.outline_variant};")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(ds.space_md, ds.space_xs, ds.space_md, ds.space_xs)
        tb.setSpacing(ds.space_sm)

        # Search
        from phibuilder.widgets import M3TextField
        self._search_field = M3TextField()
        self._search_field.setPlaceholderText("Rechercher...")
        self._search_field.setFixedHeight(ds.field_height)
        self._search_field.setStyleSheet(ds.flat_input_qss())
        self._search_field.setMinimumWidth(ds.sidebar_width - ds.space_lg)
        self._search_field.textChanged.connect(self._on_search_changed)
        tb.addWidget(self._search_field)

        # Service filter
        self._service_combo = QComboBox()
        self._service_combo.addItem("Tous les services", None)
        from Blado.common.blado_database import BladoDatabase
        for c in BladoDatabase.get_services():
            if c.get("enabled"):
                self._service_combo.addItem(c["label"], c["id"])
        self._service_combo.setFixedHeight(ds.field_height)
        self._service_combo.setStyleSheet(ds.flat_input_qss())
        self._service_combo.currentIndexChanged.connect(self._on_filter_changed)
        tb.addWidget(self._service_combo)

        # Status filter — valeurs exactes de emp_status en base
        self._status_combo = QComboBox()
        self._status_combo.addItem("Tous statuts", None)
        self._status_combo.addItem("Actif", "actif")
        self._status_combo.addItem("Suspendu", "suspendu")
        self._status_combo.addItem("En préavis", "en_préavis")
        self._status_combo.addItem("Parti", "parti")
        self._status_combo.setFixedHeight(ds.field_height)
        self._status_combo.setStyleSheet(ds.flat_input_qss())
        self._status_combo.currentIndexChanged.connect(self._on_filter_changed)
        tb.addWidget(self._status_combo)

        # Sort
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Nom", "Ancienneté", "Date d'embauche"])
        self._sort_combo.setFixedHeight(ds.field_height)
        self._sort_combo.setStyleSheet(ds.flat_input_qss())
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        tb.addWidget(self._sort_combo)

        tb.addStretch()

        # View toggle
        grid_btn = QPushButton()
        grid_btn.setIcon(md3_icon("view_module", color=p.primary, size=18))
        grid_btn.setFixedSize(ds.field_height, ds.field_height)
        grid_btn.setCursor(Qt.PointingHandCursor)
        grid_btn.setToolTip("Vue grille")
        grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        grid_btn.setStyleSheet(f"QPushButton {{ border: 1px solid {p.outline}; border-radius: {ds.radius_xs}px; background: transparent; }} QPushButton:hover {{ background: {p.surface_variant}; }}")
        tb.addWidget(grid_btn)

        table_btn = QPushButton()
        table_btn.setIcon(md3_icon("description", color=p.primary, size=18))
        table_btn.setFixedSize(ds.field_height, ds.field_height)
        table_btn.setCursor(Qt.PointingHandCursor)
        table_btn.setToolTip("Vue tableau")
        table_btn.clicked.connect(lambda: self._set_view_mode("table"))
        table_btn.setStyleSheet(f"QPushButton {{ border: 1px solid {p.outline}; border-radius: {ds.radius_xs}px; background: transparent; }} QPushButton:hover {{ background: {p.surface_variant}; }}")
        tb.addWidget(table_btn)

        # Export
        export_btn = QPushButton("CSV")
        export_btn.setFixedHeight(ds.field_height)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.primary}; border: 1px solid {p.primary};
            border-radius: {ds.radius_xs}px; padding: {ds.space_xxs}px {ds.space_xs}px; font-size: {theme_manager.font_size(11)}px; }}
            QPushButton:hover {{ background: {p.primary}; color: white; }}
        """)
        export_btn.clicked.connect(self._on_export_csv)
        tb.addWidget(export_btn)

        parent_layout.addWidget(toolbar)

    # ------------------------------------------------------------------
    # Search / filter / sort
    # ------------------------------------------------------------------
    @safe_slot("StaffGrid._on_search_changed")
    def _on_search_changed(self, text: str):
        self._search_text = text.strip()
        self.refresh()

    @safe_slot("StaffGrid._on_filter_changed")
    def _on_filter_changed(self):
        self._filter_service = self._service_combo.currentData() or None
        self._filter_status = self._status_combo.currentData()
        self.refresh()

    @safe_slot("StaffGrid._on_sort_changed")
    def _on_sort_changed(self, idx: int):
        self._sort_by = ["name", "seniority", "hire_date"][idx]
        self.refresh()

    def _set_view_mode(self, mode: str):
        self._view_mode = mode
        self.refresh()

    @safe_slot("StaffGrid._on_export_csv")
    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", "personnel.csv", "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["ID", "Nom", "Prénom", "Email", "Fonction", "Service", "Statut"])
            for d in self._all_data:
                w.writerow([d["id"], d["last_name"], d["first_name"], d.get("email",""),
                           d.get("professional_category",""), d.get("service_label",""),
                           d.get("emp_status","actif")])

    def refresh(self):
        self._load_data()
        if self._view_mode == "grid":
            self._render_grid()
        else:
            self._render_table()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._view_mode == "grid":
            self._reflow()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def _cols_for_width(self) -> int:
        avail = self._scroll.viewport().width() - MARGIN * 2
        return max(1, (avail + SPACING) // (CARD_W + SPACING))

    def _reflow(self):
        """Redistribue les widgets dans la grille après redimensionnement."""
        new_cols = self._cols_for_width()
        if new_cols == self._cols:
            return
        self._cols = new_cols

        # Construire une liste stable avant de manipuler le layout
        widgets = []
        for i in range(self._grid.count()):
            item = self._grid.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())

        # Retirer tous les widgets
        for w in widgets:
            self._grid.removeWidget(w)

        # Réinsérer dans le bon ordre
        for i, w in enumerate(widgets):
            row, col = divmod(i, new_cols)
            self._grid.addWidget(w, row, col)

    def _load_data(self):
        from Blado.common.blado_database import BladoDatabase
        filters = {
            "service_id": self._filter_service,
            "status": self._filter_status,
            "sort": self._sort_by,
        }
        self._all_data = BladoDatabase.search_staff(
            self._id_lo, self._id_hi, self._is_staff,
            search_text=self._search_text, filters=filters)

    def _render_grid(self):
        if self._table_view:
            self._table_view.hide()
        self._scroll.setWidget(self._container)

        # Nettoyer la grille
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not self._all_data:
            lbl = QLabel("Aucun employe dans ce service")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {theme_manager.palette.text_soft}; font-size: {theme_manager.font_size(13)}px;")
            self._grid.addWidget(lbl, 0, 0)
            return

        self._cols = self._cols_for_width()
        # Fixer les colonnes à largeur uniforme, espace restant à droite
        for c in range(self._cols):
            self._grid.setColumnStretch(c, 0)
        self._grid.setColumnStretch(self._cols, 1)  # spacer column
        for i, data in enumerate(self._all_data):
            card = _StaffCard(data)
            card.mouseDoubleClickEvent = lambda e, d=data: self._show_detail(d)
            self._grid.addWidget(card, i // self._cols, i % self._cols, Qt.AlignLeft | Qt.AlignTop)

    def _render_table(self):
        # Clean grid widgets
        i = self._grid.count()
        while i > 0:
            i -= 1
            item = self._grid.itemAt(i)
            if item and item.widget():
                w = self._grid.takeAt(i)
                if w.widget():
                    w.widget().deleteLater()

        # Build table if needed, add to scroll
        if not self._table_view:
            self._table_view = M3TableWidget()
            self._table_view.setEditTriggers(M3TableWidget.NoEditTriggers)
            self._table_view.setSelectionBehavior(M3TableWidget.SelectRows)
            self._table_view.setAlternatingRowColors(False)
            self._table_view.verticalHeader().setDefaultSectionSize(ds.table_row_min)
            self._table_view.setStyleSheet(ds.table_qss())
            self._table_view.doubleClicked.connect(self._on_table_double_click)

        self._scroll.setWidget(self._table_view)
        self._table_view.show()
        cols = ["ID", "Nom", "Prénom", "Email", "Rôles", "Statut"]
        self._table_view.setColumnCount(len(cols))
        self._table_view.set_headers(cols)
        self._table_view.setRowCount(0)
        self._table_view.setColumnHidden(0, True)

        for row_idx, d in enumerate(self._all_data):
            self._table_view.setRowCount(row_idx + 1)
            from PySide6.QtWidgets import QTableWidgetItem
            self._table_view.setItem(row_idx, 0, QTableWidgetItem(str(d["id"])))
            self._table_view.setItem(row_idx, 1, QTableWidgetItem(d.get("last_name", "")))
            self._table_view.setItem(row_idx, 2, QTableWidgetItem(d.get("first_name", "")))
            self._table_view.setItem(row_idx, 3, QTableWidgetItem(d.get("email", "")))
            self._table_view.setItem(row_idx, 4, QTableWidgetItem(d.get("professional_category", "")))
            self._table_view.setItem(row_idx, 5, QTableWidgetItem(d.get("emp_status", "actif")))

        self._table_view.horizontalHeader().setStretchLastSection(True)

    @safe_slot("StaffGrid._on_table_double_click")
    def _on_table_double_click(self, index):
        row = index.row()
        if 0 <= row < len(self._all_data):
            self.staff_selected.emit(self._all_data[row])
