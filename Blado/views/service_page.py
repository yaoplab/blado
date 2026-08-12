"""Blado — Gestion des services (activation de slots)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog, QFormLayout, QColorDialog,
    QTableWidgetItem, QAbstractItemView,
)
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from phibuilder.widgets.button import M3Button, ButtonVariant
from phibuilder.widgets.label import M3Label
from phibuilder.widgets.textfield import M3TextField
from phibuilder.widgets.table import M3TableWidget
from Blado.common.blado_database import BladoDatabase

COLS = ["ID", "Service", "Code", "Actif", "Employés", "Libres", "Couleur", ""]


class ServicePage(QWidget):
    """Liste des services actives + activation du prochain slot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phi = theme_manager.phi_theme
        self._services = []
        self._build_ui()
        self._load()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        header = QHBoxLayout()
        title = M3Label("Services actives")
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};")
        header.addWidget(title)
        header.addStretch()

        # Trouver le prochain service desactive
        add_btn = M3Button("+ Activer un service", variant=ButtonVariant.FILLED, theme=self._phi)
        add_btn.clicked.connect(self._on_add_service)
        # Desactiver si plus de service dispo
        free = BladoDatabase.get_first_disabled_service()
        if free is None:
            add_btn.setEnabled(False)
            add_btn.setText("Tous actives")
        header.addWidget(add_btn)
        self._add_btn = add_btn
        layout.addLayout(header)

        self._table = M3TableWidget()
        self._table.setColumnCount(len(COLS))
        self._table.setHorizontalHeaderLabels(COLS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 200)
        self._table.setColumnWidth(2, 55)
        self._table.setColumnWidth(3, 50)
        self._table.setColumnWidth(4, 70)
        self._table.setColumnWidth(5, 60)
        self._table.setColumnWidth(6, 70)
        self._table.setColumnWidth(7, 80)
        self._table.setStyleSheet(ds.table_qss())
        layout.addWidget(self._table, 1)

    def _load(self):
        # N'afficher QUE les services actives
        self._services = [s for s in (BladoDatabase.get_services() or []) if s.get("enabled")]
        self._table.setRowCount(len(self._services))
        p = theme_manager.palette
        bold = QFont()
        bold.setBold(True)

        for row, svc in enumerate(self._services):
            sid = svc["id"]
            active = svc.get("active_count", 0)
            total = svc.get("total_slots", 0)
            free = total - active
            color_hex = svc.get("color", "white")

            id_item = QTableWidgetItem(str(sid))
            id_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, id_item)

            svc_item = QTableWidgetItem(svc["label"])
            svc_item.setFont(bold)
            self._table.setItem(row, 1, svc_item)

            code_item = QTableWidgetItem(svc.get("code", ""))
            code_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, code_item)

            # Colonne Actif
            actif_item = QTableWidgetItem("Oui" if svc.get("enabled") else "Non")
            actif_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, actif_item)

            emp_item = QTableWidgetItem(str(active))
            emp_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 4, emp_item)

            free_item = QTableWidgetItem(str(free))
            free_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 5, free_item)

            color_widget = QLabel()
            color_widget.setFixedSize(32, 20)
            color_widget.setStyleSheet(
                f"background:{color_hex};border-radius:{ds.radius_xs}px;"
                f"border:1px solid {p.outline};")
            self._table.setCellWidget(row, 6, color_widget)

            edit_btn = QPushButton("Modifier")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, s=svc: self._on_edit_service(s))
            self._table.setCellWidget(row, 7, edit_btn)

        # Mettre à jour le bouton
        free_svc = BladoDatabase.get_first_disabled_service()
        if free_svc:
            self._add_btn.setEnabled(True)
            self._add_btn.setText(f"+ Activer {free_svc['label']}")
        else:
            self._add_btn.setEnabled(False)
            self._add_btn.setText("Tous actives")

    @safe_slot("service_page_add")
    def _on_add_service(self):
        """Active le premier service avec enabled=FALSE (pattern LarcRH)."""
        svc = BladoDatabase.get_first_disabled_service()
        if not svc:
            QMessageBox.information(self, "Info", "Tous les services sont deja actives.")
            return
        dlg = ServiceDialog(self._phi, svc, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            data["enabled"] = True
            BladoDatabase.create_service(data)
            BladoDatabase.create_service_gabarit(data["id"], 99)
            self._load()

    def _on_edit_service(self, svc: dict):
        dlg = ServiceDialog(self._phi, svc, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            BladoDatabase.create_service(data)
            self._load()

    @safe_slot("service_page_restyle")
    def _restyle_all(self):
        p = theme_manager.palette
        self.setStyleSheet(f"background:{p.background};")
        self._phi = theme_manager.phi_theme
        self._load()


class ServiceDialog(QDialog):
    """Dialogue d'activation/modification d'un service."""

    def __init__(self, phi, service: dict, parent=None):
        super().__init__(parent)
        self._phi = phi
        self._service = service
        self._color = service.get("color", "white")
        is_new = not service.get("enabled")
        self.setWindowTitle("Activer un service" if is_new else "Modifier le service")
        self.setMinimumWidth(450)
        self._build_ui()

    def _build_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_lg, ds.space_lg, ds.space_lg, ds.space_lg)

        form = QFormLayout()
        form.setSpacing(ds.space_sm)

        # ID (informatif)
        id_lbl = QLabel(f"ID : {self._service['id']}")
        id_lbl.setStyleSheet(f"font-size:{ds.font_body}px;color:{p.text_soft};border:none;")
        form.addRow(id_lbl)

        self._label_field = M3TextField()
        self._label_field.setFixedHeight(ds.field_height)
        self._label_field.setText(self._service.get("label", ""))
        form.addRow("Nom :", self._label_field)

        self._code_field = M3TextField()
        self._code_field.setFixedHeight(ds.field_height)
        self._code_field.setText(self._service.get("code", ""))
        form.addRow("Code :", self._code_field)

        self._desc_field = M3TextField()
        self._desc_field.setFixedHeight(ds.field_height)
        self._desc_field.setText(self._service.get("description", ""))
        form.addRow("Description :", self._desc_field)

        self._color_btn = QPushButton(self._color)
        self._color_btn.setFixedHeight(ds.field_height)
        self._color_btn.setStyleSheet(
            f"background:{self._color};font-weight:bold;"
            f"border-radius:{ds.radius_xs}px;")
        self._color_btn.clicked.connect(self._pick_color)
        form.addRow("Couleur :", self._color_btn)

        layout.addLayout(form)
        layout.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = M3Button("Annuler", variant=ButtonVariant.OUTLINED, theme=self._phi)
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = M3Button("Enregistrer", variant=ButtonVariant.FILLED, theme=self._phi)
        save.clicked.connect(self.accept)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _pick_color(self):
        from PySide6.QtGui import QColor
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self._color_btn.setText(self._color)
            self._color_btn.setStyleSheet(
                f"background:{self._color};font-weight:bold;"
                f"border-radius:{ds.radius_xs}px;")

    def get_data(self) -> dict:
        return {
            "id": self._service["id"],
            "label": self._label_field.text() or self._service["label"],
            "code": self._code_field.text(),
            "description": self._desc_field.text(),
            "color": self._color,
        }
