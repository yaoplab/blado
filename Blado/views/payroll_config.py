"""Blado — Configuration de la paie (taux CNSS, barèmes, majorations)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.safe_slot import safe_slot
from bladocommon.icons import icon
from phibuilder.widgets.button import M3Button, ButtonVariant
from phibuilder.widgets.textfield import M3TextField
from phibuilder.widgets.label import M3Label
from Blado.common.blado_database import BladoDatabase


class PayrollConfigPage(QWidget):
    """Page de configuration des paramètres de paie."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phi = theme_manager.phi_theme
        self._cfg = BladoDatabase.get_payroll_config()
        self._fields = {}
        self._build_ui()
        ds.theme_changed.connect(self._restyle_all)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_lg)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        # Titre
        title = M3Label("Configuration de la paie")
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{theme_manager.palette.text_strong};")
        layout.addWidget(title)

        # Section CNSS
        layout.addWidget(self._section_card(
            "Cotisations CNSS",
            [
                ("cnss_employe", "Cotisation employé (%)", "4.0"),
                ("cnss_employeur", "Cotisation employeur (%)", "16.5"),
                ("cnss_plafond", "Salaire plafond CNSS (FCFA)", "300 000"),
            ]
        ))

        # Section Heures Sup
        layout.addWidget(self._section_card(
            "Majorations heures supplémentaires",
            [
                ("taux_hsup_15", "Majoration 15% (8h/j → 40h/sem)", "115"),
                ("taux_hsup_20", "Majoration 20% (41-48h/sem)", "120"),
                ("taux_hsup_40", "Majoration 40% (>48h ou dimanche)", "140"),
            ]
        ))

        # Section SMIC
        layout.addWidget(self._section_card(
            "Salaire minimum",
            [
                ("smic_mensuel", "SMIC mensuel Togo (FCFA)", "35 000"),
            ]
        ))

        layout.addStretch()

        # Bouton sauvegarde
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = M3Button("Sauvegarder", variant=ButtonVariant.FILLED, theme=self._phi)
        save_btn.setIcon(icon("save", color=theme_manager.palette.on_primary, size=ds.icon_sm))
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    @safe_slot("payroll_config_save")
    def _on_save(self):
        for key, field in self._fields.items():
            try:
                value = float(field.text().replace(" ", "").replace(",", "."))
                BladoDatabase.save_payroll_config(key, value)
            except ValueError:
                pass
        self._cfg = BladoDatabase.get_payroll_config()

    def _section_card(self, title: str, fields: list[tuple[str, str, str]]):
        p = theme_manager.palette
        card = QWidget()
        card.setStyleSheet(
            f"background:{p.surface};border:1px solid {p.outline};"
            f"border-radius:{ds.radius_sm}px;"
        )
        cl = QVBoxLayout(card)
        cl.setSpacing(ds.space_sm)
        cl.setContentsMargins(ds.space_md, ds.space_md, ds.space_md, ds.space_md)

        # Titre section
        header = QLabel(title)
        header.setStyleSheet(f"font-size:{ds.font_title}px;font-weight:bold;color:{p.text_strong};")
        cl.addWidget(header)

        for key, label, default in fields:
            row = QHBoxLayout()
            row.setSpacing(ds.space_sm)
            lbl = M3Label(label)
            lbl.setStyleSheet(f"color:{p.text_soft};font-size:{ds.font_body}px;")
            lbl.setMinimumWidth(280)
            row.addWidget(lbl)

            val = str(self._cfg.get(key, float(default.replace(" ", ""))))
            field = M3TextField()
            field.setText(val)
            field.setFixedWidth(120)
            field.setFixedHeight(ds.field_height)
            field.setStyleSheet(ds.flat_input_qss())
            row.addWidget(field)
            row.addStretch()
            self._fields[key] = field
            cl.addLayout(row)

        return card

    @safe_slot("payroll_config_restyle")
    def _restyle_all(self):
        self._phi = theme_manager.phi_theme
        p = theme_manager.palette
        self.setStyleSheet(f"background:{p.background};")
        self._build_ui()
