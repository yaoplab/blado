"""Blado — Lancement de la paie mensuelle."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QMessageBox, QProgressBar,
)
from PySide6.QtCore import QDate
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from bladocommon.icons import icon
from bladocommon.session import session
from phibuilder.widgets.button import M3Button, ButtonVariant
from phibuilder.widgets.label import M3Label
from phibuilder.widgets.combo import M3ComboBox
from Blado.common.blado_database import BladoDatabase


class PayslipRunPage(QWidget):
    """Page de lancement de la paie mensuelle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phi = theme_manager.phi_theme
        self._build_ui()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_lg)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        # Titre
        title = M3Label("Lancement de la paie")
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};")
        layout.addWidget(title)

        # Sélecteurs mois/année
        sel_row = QHBoxLayout()
        sel_row.setSpacing(ds.space_md)

        lbl = M3Label("Période :")
        lbl.setStyleSheet(f"color:{p.text_strong};font-size:{ds.font_title}px;")
        sel_row.addWidget(lbl)

        self._month_combo = QComboBox()
        months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        for i, m in enumerate(months):
            self._month_combo.addItem(m, i + 1)
        today = QDate.currentDate()
        self._month_combo.setCurrentIndex(today.month() - 1)
        self._month_combo.setStyleSheet(ds.flat_input_qss())
        sel_row.addWidget(self._month_combo)

        self._year_combo = QComboBox()
        for y in range(2024, today.year() + 2):
            self._year_combo.addItem(str(y), y)
        self._year_combo.setCurrentText(str(today.year()))
        self._year_combo.setStyleSheet(ds.flat_input_qss())
        sel_row.addWidget(self._year_combo)

        sel_row.addStretch()
        layout.addLayout(sel_row)

        # Progression
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(ds.space_lg)
        layout.addWidget(self._progress)

        # Résumé après génération
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"color:{p.text_soft};font-size:{ds.font_body}px;")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        layout.addStretch()

        # Boutons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        preview_btn = M3Button("Prévisualiser", variant=ButtonVariant.OUTLINED, theme=self._phi)
        preview_btn.setIcon(icon("visibility", color=p.primary, size=ds.icon_sm))
        preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(preview_btn)

        self._run_btn = M3Button("Lancer la paie", variant=ButtonVariant.FILLED, theme=self._phi)
        self._run_btn.setIcon(icon("bolt", color=p.on_primary, size=ds.icon_sm))
        self._run_btn.clicked.connect(self._on_run)
        btn_row.addWidget(self._run_btn)

        layout.addLayout(btn_row)

    @safe_slot("payslip_run_preview")
    def _on_preview(self):
        month = self._month_combo.currentData()
        year = self._year_combo.currentData()
        entreprise_id = session.entreprise_id if session.mode == "consultant" else None

        journal = BladoDatabase.get_payroll_journal(month, year, entreprise_id)
        if not journal or journal.get("nb_bulletins", 0) == 0:
            self._summary.setText(
                f"📋 Aucun bulletin existant pour {self._month_combo.currentText()} {year}.\n"
                "Cliquez sur « Lancer la paie » pour générer les bulletins."
            )
        else:
            self._summary.setText(
                f"📊 {journal['nb_bulletins']} bulletins déjà générés\n"
                f"   Brut total : {int(journal['total_brut']):,} FCFA\n"
                f"   Net total  : {int(journal['total_net']):,} FCFA\n"
                f"   CNSS emp.  : {int(journal['total_cnss']):,} FCFA\n"
                f"   Impôts     : {int(journal['total_impots']):,} FCFA"
            )

    @safe_slot("payslip_run_execute")
    def _on_run(self):
        month = self._month_combo.currentData()
        year = self._year_combo.currentData()
        entreprise_id = session.entreprise_id if session.mode == "consultant" else None

        reply = QMessageBox.question(
            self, "Confirmer",
            f"Lancer la paie pour {self._month_combo.currentText()} {year} ?\n"
            "Les bulletins existants seront recalculés.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._progress.setVisible(True)
        self._progress.setMaximum(0)  # indéterminé

        count = BladoDatabase.run_monthly_payroll(month, year, entreprise_id)

        self._progress.setMaximum(1)
        self._progress.setValue(1)
        self._progress.setVisible(False)

        if count <= 0:
            self._summary.setText(
                f"⚠️ Aucun bulletin généré pour {self._month_combo.currentText()} {year}.\n"
                "Vérifiez que des employés actifs ont un contrat actif."
            )
            QMessageBox.warning(
                self, "Paie",
                f"Aucun bulletin généré pour {self._month_combo.currentText()} {year}.\n\n"
                "Vérifiez que des employés actifs ont un contrat actif.",
            )
            return

        self._summary.setText(f"✅ {count} bulletins générés avec succès.")
        QMessageBox.information(self, "Paie terminée", f"{count} bulletins générés.")

    @safe_slot("payslip_run_restyle")
    def _restyle_all(self):
        self._phi = theme_manager.phi_theme
        p = theme_manager.palette
        self.setStyleSheet(f"background:{p.background};")
        self._build_ui()
