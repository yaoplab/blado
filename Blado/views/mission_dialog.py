"""Blado — Missions contractuelles (mode Consultant)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QFormLayout,
    QTableWidgetItem, QAbstractItemView, QCheckBox, QComboBox, QMessageBox,
    QDateEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
)
from PySide6.QtCore import QDate

from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from phibuilder.widgets.button import M3Button, ButtonVariant
from phibuilder.widgets.label import M3Label
from phibuilder.widgets.textfield import M3TextField
from phibuilder.widgets.table import M3TableWidget
from Blado.common.blado_database import BladoDatabase

MISSION_TYPES = ['gestion_rh_complete', 'paie', 'recrutement', 'formation', 'audit_rh', 'interim', 'autre']
STATUTS = ['brouillon', 'active', 'suspendue', 'terminee', 'resiliee']


class MissionPage(QWidget):
    """Dashboard des missions (mode Consultant)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phi = theme_manager.phi_theme
        self._missions = []
        self._build_ui()
        self._load()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        hdr = QHBoxLayout()
        title = M3Label("Missions contractuelles")
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};")
        hdr.addWidget(title)
        hdr.addStretch()
        add_btn = M3Button("+ Nouvelle mission", variant=ButtonVariant.FILLED, theme=self._phi)
        add_btn.clicked.connect(self._on_add)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # KPIs
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(ds.space_md)
        for lbl in ["Missions actives", "Montant total", "Total missions"]:
            kpi = self._make_kpi(lbl, "—")
            self._kpi_row.addWidget(kpi)
        layout.addLayout(self._kpi_row)

        # Table
        self._table = M3TableWidget()
        self._table.set_headers(["Réf", "Entreprise", "Type", "Début", "Fin", "Montant", "Statut", ""])
        self._table.setStyleSheet(ds.table_qss())
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 130)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 90)
        self._table.setColumnWidth(5, 100)
        self._table.setColumnWidth(6, 80)
        layout.addWidget(self._table, 1)

    def _make_kpi(self, label: str, value: str) -> QWidget:
        p = theme_manager.palette
        card = QWidget()
        card.setFixedHeight(ds.kpi_card_height)
        card.setStyleSheet(f"background:{p.surface};border:1px solid {p.outline_variant};border-radius:{ds.radius_sm}px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(ds.space_sm, ds.space_xs, ds.space_sm, ds.space_xs)
        cl.setSpacing(2)
        vl = QLabel(value)
        vl.setStyleSheet(f"font-size:{ds.font_h1}px;font-weight:bold;color:{p.primary};border:none;")
        vl.setObjectName("kpi_val")
        cl.addWidget(vl)
        ll = QLabel(label)
        ll.setStyleSheet(f"font-size:{ds.font_small}px;color:{p.text_soft};border:none;")
        cl.addWidget(ll)
        return card

    def _load(self):
        self._missions = BladoDatabase.get_missions() or []
        kpis = BladoDatabase.get_missions_kpis()
        # Update KPIs
        for i, key in enumerate(["actives", "montant_total", "total"]):
            w = self._kpi_row.itemAt(i).widget()
            lbl = w.findChild(QLabel, "kpi_val")
            if lbl:
                val = kpis.get(key, 0)
                if key == "montant_total":
                    lbl.setText(f"{int(val):,} FCFA")
                else:
                    lbl.setText(str(int(val)))

        # Table
        for i in range(self._table.rowCount() - 1, -1, -1):
            self._table.removeRow(i)
        for m in self._missions:
            debut = m.get("date_debut")
            fin = m.get("date_fin")
            self._table.add_row([
                m.get("reference", ""),
                m.get("entreprise_nom", ""),
                m.get("type_mission", "").replace("_", " ").title(),
                str(debut)[:10] if debut else "",
                str(fin)[:10] if fin else "—",
                f"{int(m.get('montant', 0)):,} {m.get('devise','XOF')}",
                m.get("statut", ""),
                "✏️ Modifier",
            ])
        # Click handler
        self._table.cellDoubleClicked.connect(self._on_cell_double_click)

    def _on_cell_double_click(self, row, col):
        if 0 <= row < len(self._missions):
            self._on_edit(self._missions[row])

    @safe_slot("MissionPage._on_add")
    def _on_add(self):
        dlg = MissionDialog(self._phi, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            BladoDatabase.save_mission(data)
            self._load()

    def _on_edit(self, mission: dict):
        dlg = MissionDialog(self._phi, mission, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            data["id"] = mission["id"]
            BladoDatabase.save_mission(data)
            self._load()

    @safe_slot("MissionPage._restyle")
    def _restyle_all(self):
        self.setStyleSheet(f"background:{theme_manager.palette.background};")
        self._phi = theme_manager.phi_theme
        self._load()


class MissionDialog(QDialog):
    """Dialogue de création/édition d'une mission."""

    def __init__(self, phi, mission: dict | None = None, parent=None):
        super().__init__(parent)
        self._phi = phi
        self._mission = mission
        self.setWindowTitle("Nouvelle mission" if mission is None else "Modifier la mission")
        self.setMinimumWidth(550)
        self._build_ui()

    def _build_ui(self):
        p = theme_manager.palette
        m = self._mission or {}
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_lg, ds.space_lg, ds.space_lg, ds.space_lg)

        form = QFormLayout()
        form.setSpacing(ds.space_sm)

        # Consultant
        self._cb_consultant = QComboBox()
        self._cb_consultant.setFixedHeight(ds.field_height)
        self._cb_consultant.setStyleSheet(ds.flat_input_qss())
        consultants = BladoDatabase.get_consultants()
        for c in consultants:
            self._cb_consultant.addItem(c["nom"], c["id"])
        form.addRow("Consultant :", self._cb_consultant)

        # Entreprise
        self._cb_entreprise = QComboBox()
        self._cb_entreprise.setFixedHeight(ds.field_height)
        self._cb_entreprise.setStyleSheet(ds.flat_input_qss())
        entreprises = BladoDatabase.get_entreprises()
        for e in entreprises:
            self._cb_entreprise.addItem(e["nom"], e["id"])
        form.addRow("Entreprise :", self._cb_entreprise)

        self._f_ref = M3TextField(); self._f_ref.setFixedHeight(ds.field_height)
        self._f_ref.setText(m.get("reference", ""))
        form.addRow("Référence :", self._f_ref)

        self._f_titre = M3TextField(); self._f_titre.setFixedHeight(ds.field_height)
        self._f_titre.setText(m.get("titre", ""))
        form.addRow("Titre :", self._f_titre)

        self._cb_type = QComboBox(); self._cb_type.setFixedHeight(ds.field_height)
        self._cb_type.setStyleSheet(ds.flat_input_qss())
        for t in MISSION_TYPES:
            self._cb_type.addItem(t.replace("_", " ").title(), t)
        form.addRow("Type :", self._cb_type)

        self._f_debut = QDateEdit(); self._f_debut.setFixedHeight(ds.field_height)
        self._f_debut.setCalendarPopup(True)
        if m.get("date_debut"):
            self._f_debut.setDate(m["date_debut"])
        form.addRow("Début :", self._f_debut)

        self._f_fin = QDateEdit(); self._f_fin.setFixedHeight(ds.field_height)
        self._f_fin.setCalendarPopup(True)
        if m.get("date_fin"):
            self._f_fin.setDate(m["date_fin"])
        else:
            self._f_fin.setDate(QDate.currentDate().addYears(1))
        form.addRow("Fin :", self._f_fin)

        self._f_montant = QDoubleSpinBox(); self._f_montant.setFixedHeight(ds.field_height)
        self._f_montant.setMaximum(999999999); self._f_montant.setValue(float(m.get("montant", 0)))
        form.addRow("Montant :", self._f_montant)

        self._cb_statut = QComboBox(); self._cb_statut.setFixedHeight(ds.field_height)
        self._cb_statut.setStyleSheet(ds.flat_input_qss())
        for s in STATUTS:
            self._cb_statut.addItem(s.title(), s)
        if m.get("statut"):
            self._cb_statut.setCurrentText(m["statut"].title())
        form.addRow("Statut :", self._cb_statut)

        # Périmètre
        scope_lbl = QLabel("Périmètre RH couvert :")
        scope_lbl.setStyleSheet(f"font-weight:bold;color:{p.text_strong};")
        form.addRow(scope_lbl)
        scope_grid = QHBoxLayout()
        scope_grid.setSpacing(ds.space_md)
        self._checks = {}
        for key, lbl in [("gerer_paie","Paie"),("gerer_contrats","Contrats"),("gerer_conges","Congés"),
                         ("gerer_recrutement","Recrutement"),("gerer_discipline","Discipline"),("gerer_documents","Documents")]:
            cb = QCheckBox(lbl)
            cb.setChecked(m.get(key, False))
            self._checks[key] = cb
            scope_grid.addWidget(cb)
        form.addRow("", scope_grid)

        layout.addLayout(form)
        layout.addStretch()

        btns = QHBoxLayout(); btns.addStretch()
        cancel = M3Button("Annuler", variant=ButtonVariant.OUTLINED, theme=self._phi)
        cancel.clicked.connect(self.reject); btns.addWidget(cancel)
        save = M3Button("Enregistrer", variant=ButtonVariant.FILLED, theme=self._phi)
        save.clicked.connect(self.accept); btns.addWidget(save)
        layout.addLayout(btns)

    def get_data(self) -> dict:
        return {
            "consultant_id": self._cb_consultant.currentData(),
            "entreprise_id": self._cb_entreprise.currentData(),
            "reference": self._f_ref.text().strip(),
            "titre": self._f_titre.text().strip(),
            "type_mission": self._cb_type.currentData(),
            "date_debut": self._f_debut.date().toPython(),
            "date_fin": self._f_fin.date().toPython(),
            "montant": self._f_montant.value(),
            "statut": self._cb_statut.currentData(),
            **{k: cb.isChecked() for k, cb in self._checks.items()},
        }
