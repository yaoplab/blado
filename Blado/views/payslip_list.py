"""Blado — Journal de paie (liste des bulletins par mois)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import QDate
from PySide6.QtGui import QFont
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from bladocommon.session import session
from phibuilder.widgets.label import M3Label
from phibuilder.widgets.button import M3Button, ButtonVariant
from phibuilder.widgets.table import M3TableWidget
from Blado.common.blado_database import BladoDatabase


class PayslipListPage(QWidget):
    """Journal de paie — liste des bulletins avec totaux."""

    MONTHS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phi = theme_manager.phi_theme
        self._payslips = []
        self._build_ui()
        self._load()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        # En-tête
        header = QHBoxLayout()
        title = M3Label("Journal de paie")
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};")
        header.addWidget(title)
        header.addStretch()

        # Bouton lancement
        btn = M3Button("Lancer la paie", variant=ButtonVariant.FILLED, theme=self._phi)
        btn.clicked.connect(self._on_launch_clicked)
        header.addWidget(btn)
        layout.addLayout(header)

        # Totaux
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(ds.space_md)
        self._kpi_widgets = []
        for label in ["Bulletins", "Brut total", "Net total", "CNSS", "Impôts"]:
            kpi = self._make_kpi_card(label, "—")
            self._kpi_widgets.append(kpi)
            self._kpi_row.addWidget(kpi)
        layout.addLayout(self._kpi_row)

        # Tableau
        self._table = M3TableWidget()
        self._table.set_headers(["Employé", "Matricule", "Service", "Brut", "Primes",
                                 "CNSS", "Impôts", "Net", "Statut"])
        self._table.setStyleSheet(ds.table_qss())
        layout.addWidget(self._table)

    def _make_kpi_card(self, label: str, value: str) -> QWidget:
        p = theme_manager.palette
        card = QWidget()
        card.setFixedHeight(ds.kpi_card_height)
        card.setStyleSheet(
            f"background:{p.surface};border:1px solid {p.outline};"
            f"border-radius:{ds.radius_sm}px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(ds.space_sm, ds.space_xs, ds.space_sm, ds.space_xs)
        cl.setSpacing(ds.space_xxs)

        lbl_title = M3Label(label)
        lbl_title.setStyleSheet(f"color:{p.text_soft};font-size:{ds.font_small}px;")
        cl.addWidget(lbl_title)

        lbl_val = M3Label(value)
        lbl_val.setStyleSheet(f"color:{p.text_strong};font-size:{ds.font_h1}px;font-weight:bold;")
        lbl_val.setObjectName(f"kpi_val_{label}")
        cl.addWidget(lbl_val)
        return card

    @safe_slot("payslip_list_load")
    def _load(self):
        today = QDate.currentDate()
        month, year = today.month(), today.year()
        ent_id = session.entreprise_id if session.mode == "consultant" else None

        self._payslips = BladoDatabase.get_payslips(month, year, ent_id)
        journal = BladoDatabase.get_payroll_journal(month, year, ent_id)

        # KPIs
        vals = [
            str(journal.get("nb_bulletins", 0)),
            f"{int(journal.get('total_brut', 0)):,}",
            f"{int(journal.get('total_net', 0)):,}",
            f"{int(journal.get('total_cnss', 0)):,}",
            f"{int(journal.get('total_impots', 0)):,}",
        ]
        for w, v in zip(self._kpi_widgets, vals):
            lbl = w.findChild(M3Label, f"kpi_val_{w.findChild(M3Label).text()}")
            if lbl:
                lbl.setText(v)

        # Tableau
        self._table.clear()
        bold = QFont()
        bold.setBold(True)
        for ps in self._payslips:
            name = f"{ps['last_name']} {ps['first_name']}"
            self._table.add_row([
                name, ps.get("matricule", ""), ps.get("service_label", ""),
                f"{int(ps['salaire_brut']):,}", f"{int(ps['total_primes']):,}",
                f"{int(ps['cnss_employe']):,}", f"{int(ps['impots']):,}",
                f"{int(ps['net_a_payer']):,}", ps.get("statut", "brouillon"),
            ])

    @safe_slot("payslip_list_launch")
    def _on_launch_clicked(self):
        # La page est reparentée par le QStackedWidget : remonter jusqu'à la
        # fenêtre principale (qui possède _switch_to), pas au parent direct.
        win = self.window()
        if win is not None and hasattr(win, "_switch_to"):
            win._switch_to("payslip_run")
        else:
            QMessageBox.warning(self, "Paie", "Impossible d'ouvrir le lancement de la paie.")

    @safe_slot("payslip_list_restyle")
    def _restyle_all(self):
        self._phi = theme_manager.phi_theme
        self._build_ui()
        self._load()
