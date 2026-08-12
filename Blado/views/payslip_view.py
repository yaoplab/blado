"""Blado — Aperçu détaillé d'un bulletin de paie."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QFont
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from phibuilder.widgets.label import M3Label
from phibuilder.widgets.button import M3Button, ButtonVariant
from Blado.common.blado_database import BladoDatabase


class PayslipViewWidget(QWidget):
    """Affichage détaillé d'un bulletin de paie."""

    def __init__(self, payslip_id: int, parent=None):
        super().__init__(parent)
        self._payslip_id = payslip_id
        self._phi = theme_manager.phi_theme
        self._build_ui()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        p = theme_manager.palette
        ps = BladoDatabase.get_payslip(self._payslip_id)
        if not ps:
            self._show_empty()
            return

        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        # En-tête employé
        name = f"{ps['last_name']} {ps['first_name']}"
        emp_label = M3Label(f"Bulletin de paie — {name}")
        emp_label.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};")
        layout.addWidget(emp_label)

        sub = M3Label(f"Matricule : {ps.get('matricule', '-')} | Service : {ps.get('service_label', '-')} | "
                      f"Période : {ps['period_month']:02d}/{ps['period_year']}")
        sub.setStyleSheet(f"color:{p.text_soft};font-size:{ds.font_body}px;")
        layout.addWidget(sub)

        # Lignes du bulletin (GAINS à gauche, DEDUCTIONS à droite)
        gains = [l for l in ps["lines"] if l["type"] == "gain"]
        deductions = [l for l in ps["lines"] if l["type"] == "deduction"]

        lines_layout = QHBoxLayout()
        lines_layout.setSpacing(ds.space_xl)

        # Colonne GAINS
        gain_widget = self._lines_column("Gains", gains, p)
        lines_layout.addWidget(gain_widget)

        # Colonne DEDUCTIONS
        ded_widget = self._lines_column("Retenues", deductions, p)
        lines_layout.addWidget(ded_widget)

        layout.addLayout(lines_layout)

        # Récapitulatif
        recap = QWidget()
        recap.setStyleSheet(
            f"background:{p.surface_variant if hasattr(p, 'surface_variant') else p.surface};"
            f"border:1px solid {p.outline};border-radius:{ds.radius_sm}px;"
        )
        rl = QVBoxLayout(recap)
        rl.setSpacing(ds.space_xs)
        rl.setContentsMargins(ds.space_md, ds.space_md, ds.space_md, ds.space_md)

        bold = QFont()
        bold.setBold(True)
        brut_lbl = M3Label(f"Salaire brut : {int(ps['salaire_brut']):,} FCFA")
        brut_lbl.setFont(bold)
        rl.addWidget(brut_lbl)

        cnss_lbl = M3Label(f"CNSS (4%) : -{int(ps['cnss_employe']):,} FCFA")
        cnss_lbl.setStyleSheet(f"color:{p.error};")
        rl.addWidget(cnss_lbl)

        impots_lbl = M3Label(f"Impôts : -{int(ps['impots']):,} FCFA")
        impots_lbl.setStyleSheet(f"color:{p.error};")
        rl.addWidget(impots_lbl)

        net_lbl = M3Label(f"Net à payer : {int(ps['net_a_payer']):,} FCFA")
        net_lbl.setStyleSheet(f"font-size:{ds.font_h1}px;font-weight:bold;color:{p.success};")
        rl.addWidget(net_lbl)
        layout.addWidget(recap)

        layout.addStretch()

    def _lines_column(self, title, lines, p):
        col = QWidget()
        cl = QVBoxLayout(col)
        cl.setSpacing(ds.space_xs)

        header = M3Label(title)
        header.setStyleSheet(f"font-size:{ds.font_title}px;font-weight:bold;color:{p.text_strong};")
        cl.addWidget(header)

        if not lines:
            empty = M3Label("— Aucune ligne —")
            empty.setStyleSheet(f"color:{p.text_disabled};font-size:{ds.font_small}px;")
            cl.addWidget(empty)
        else:
            for line in lines:
                row = QHBoxLayout()
                lbl = M3Label(line["label"])
                lbl.setStyleSheet(f"color:{p.text_strong};font-size:{ds.font_body}px;")
                row.addWidget(lbl)
                row.addStretch()
                amt = M3Label(f"{int(line['montant']):,} FCFA")
                color = p.success if line["type"] == "gain" else p.error
                amt.setStyleSheet(f"color:{color};font-size:{ds.font_body}px;")
                row.addWidget(amt)
                cl.addLayout(row)
        return col

    def _show_empty(self):
        layout = QVBoxLayout(self)
        lbl = M3Label("Bulletin introuvable.")
        lbl.setStyleSheet(f"color:{theme_manager.palette.error};font-size:{ds.font_title}px;")
        layout.addWidget(lbl)

    @safe_slot("payslip_view_restyle")
    def _restyle_all(self):
        self._phi = theme_manager.phi_theme
        self._build_ui()
