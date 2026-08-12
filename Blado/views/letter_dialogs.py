# Blado — Dialogues de courriers extraits de LetterManager
# BLADO: fichier ≤ 1000 lignes (règle pyside6-wrapper)

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QScrollArea, QFrame, QLineEdit, QTextEdit,
    QComboBox, QMessageBox, QFileDialog,
)
from bladocommon.database import db
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.icons import icon as md3_icon
from bladocommon.safe_slot import safe_slot
from bladocommon.widgets.themed_widget import ThemedDialog
from Blado.common.blado_database import BladoDatabase
from Blado.views import letter_templates
class _GenerateLetterDialog(ThemedDialog):

    def __init__(self, template: dict, staff_data: dict | None = None,
                 Service: dict | None = None, parent=None):
        super().__init__(parent)
        self._template = template
        self._staff = staff_data
        self._Service = Service
        self._output_path = ""
        self.setWindowTitle(f"Générer — {template.get('title', '')}")
        _w = ds.golden_width(ds.kpi_card_height * 7)
        self.setMinimumSize(_w, ds.sp(SpacingToken.XXXL) * 3)
        self._setup_ui()

    @property
    def _STYLE(self) -> str:
        return f"GenerateLetterDialog {{ background: {theme_manager.palette.surface}; }}"

    @safe_slot("GenerateLetterDialog._restyle")
    def _restyle(self):
        try:
            self.setStyleSheet(self._STYLE)
        except RuntimeError:
            pass

    def _setup_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(ds.space_md, ds.space_md, ds.space_md, ds.space_md)
        layout.setSpacing(ds.space_sm)

        titre = QLabel(self._template.get("title", ""))
        titre.setStyleSheet(f"font-size: {s(16)}px; font-weight: bold; color: {p.text_strong}; border: none;")
        layout.addWidget(titre)

        desc = QLabel(self._template.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: {s(12)}px; color: {p.text_soft}; border: none;")
        layout.addWidget(desc)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {p.outline_variant}; border: none;")
        layout.addWidget(sep)

        # Destinataire
        layout.addWidget(QLabel("Destinataire"))
        if self._staff:
            info = f"{self._staff.get('full_name', '—')}  |  ID {self._staff.get('id', '—')}"
        else:
            info = "Aucun employé sélectionné"
        lbl = QLabel(info)
        lbl.setStyleSheet(f"font-size: {s(13)}px; color: {p.text_strong}; border: none;")
        layout.addWidget(lbl)

        # Objet
        layout.addWidget(QLabel("Objet"))
        dflt = self._template.get("title", "")
        if self._staff:
            dflt = f"{dflt} — {self._staff.get('full_name', '')}"
        self._objet_field = QLineEdit(dflt)
        self._objet_field.setFixedHeight(ds.field_height)
        self._objet_field.setStyleSheet(ds.flat_input_qss())
        layout.addWidget(self._objet_field)

        # Réf
        layout.addWidget(QLabel("Numéro de référence"))
        ref = f"RH/{date.today().year}/{self._template.get('code', '')}/{date.today().strftime('%m')}"
        self._ref_field = QLineEdit(ref)
        self._ref_field.setFixedHeight(ds.field_height)
        self._ref_field.setStyleSheet(ds.flat_input_qss())
        layout.addWidget(self._ref_field)

        # Corps
        layout.addWidget(QLabel("Corps du courrier"))
        self._body_edit = QTextEdit()
        self._body_edit.setMinimumHeight(ds.kpi_card_height * 3)
        self._body_edit.setStyleSheet(f"""
            QTextEdit {{ background: {p.background}; border: 1px solid {p.outline};
            border-radius: {ds.radius_xs}px; padding: {ds.space_sm}px;
            color: {p.text_strong}; font-size: {s(12)}px; }}
            QTextEdit:focus {{ border-color: {p.primary}; }}
        """)
        layout.addWidget(self._body_edit)
        self._fill_body()
        layout.addStretch()

        # Boutons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setFixedHeight(ds.field_height + ds.space_xs)
        cancel.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.text_strong};
            border: 1px solid {p.outline}; border-radius: {ds.radius_sm}px;
            padding: {ds.space_xs}px {ds.space_md}px; font-size: {s(13)}px; }}
            QPushButton:hover {{ background: {p.surface_variant}; }}
        """)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        save = QPushButton("Générer et sauvegarder")
        save.setCursor(Qt.PointingHandCursor)
        save.setFixedHeight(ds.field_height + ds.space_xs)
        save.setStyleSheet(f"""
            QPushButton {{ background: {p.primary}; color: white; border: none;
            border-radius: {ds.radius_sm}px; padding: {ds.space_xs}px {ds.space_md}px;
            font-size: {s(13)}px; font-weight: bold; }}
            QPushButton:hover {{ background: {p.primary}; }}
        """)
        save.clicked.connect(self._on_generate)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)
        self.setStyleSheet(self._STYLE)

    def _fill_body(self):
        staff = self._staff or {}
        code = self._template.get("code", "")
        body = build_letter(staff, code, self._objet_field.text(),
                           self._ref_field.text(), Service=self._Service,
                           template=self._template)
        self._body_edit.setPlainText(body)
        self._body_initial = body  # pour détecter les modifications utilisateur

    @safe_slot("GenerateLetterDialog._on_generate")
    def _on_generate(self):
        default_name = f"courrier_{self._template.get('code', '')}.docx"
        fpath, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le courrier", default_name,
            "Word (*.docx);;PDF (*.pdf);;Texte (*.txt)")
        if not fpath:
            return
        edited = self._body_edit.toPlainText()
        if fpath.lower().endswith(".txt"):
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(edited)
        else:
            try:
                # Si l'utilisateur a modifié le texte, extraire le corps seul
                # pour éviter de dupliquer en-tête/pied dans le DOCX formaté
                body_override = None
                if edited != getattr(self, "_body_initial", ""):
                    body_override = render_body(
                        self._staff, self._template.get("code", ""),
                        template=self._template)
                    # Si le corps extrait du build est différent du corps
                    # extrait du texte édité, on utilise le texte édité
                    body_override = _extract_body_from_full(edited)
                generate_docx(staff=self._staff,
                    code=self._template.get("code", ""),
                    objet=self._objet_field.text(), ref=self._ref_field.text(),
                    Service=self._Service, output_path=fpath,
                    template=self._template, body_override=body_override)
            except Exception as exc:
                import traceback; traceback.print_exc()
                QMessageBox.warning(self, "Erreur", f"Erreur :\n{exc}")
                return
        if self._staff:
            BladoDatabase.save_generated_letter(
                self._staff["id"], self._template["id"], fpath,
                reference=self._ref_field.text(), generated_by=session.user_id)
        QMessageBox.information(self, "Courrier généré", f"Courrier enregistré :\n{fpath}")
        self.accept()


# ════════════════════════════════════════════════════════════════════
# Dialogue sélection modèle standard (catalogue)
# ════════════════════════════════════════════════════════════════════

class _CatalogDialog(ThemedDialog):
    """Catalogue des modèles standards — sélection → duplication automatique,
    avec aperçu du corps du courrier."""

    template_chosen = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Catalogue des modèles")
        self.setMinimumSize(ds.golden_width(700), ds.golden_height(500))
        self._current_family: str | None = None
        self._selected_template: dict | None = None
        self._setup_ui()
        self._select_first()

    @property
    def _STYLE(self) -> str:
        return f"QDialog {{ background: {theme_manager.palette.background}; }}"

    @safe_slot("_CatalogDialog._restyle")
    def _restyle(self):
        try:
            self.setStyleSheet(self._STYLE)
        except RuntimeError:
            pass

    def _setup_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar familles ──
        sidebar = QWidget()
        sidebar.setFixedWidth(170)
        sidebar.setStyleSheet(f"background: {p.surface_variant}; border-right: 1px solid {p.outline_variant};")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(ds.space_xs, ds.space_sm, ds.space_xs, ds.space_sm)
        sl.setSpacing(ds.space_xxs)

        sl.addWidget(QLabel("Familles"))
        self._cat_btns: dict[str, QPushButton] = {}
        for fam_key, fam_label in FAMILIES:
            btn = QPushButton(fam_label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(ds.field_height)
            btn.setStyleSheet(f"""
                QPushButton {{ text-align: left; padding: {ds.space_xxs}px {ds.space_xs}px;
                border: none; border-radius: {ds.radius_xs}px; color: {p.text_strong};
                font-size: {s(12)}px; background: transparent; }}
                QPushButton:checked {{ background: {p.primary_container}; color: {p.primary}; font-weight: bold; }}
                QPushButton:hover {{ background: {p.surface}; }}
            """)
            btn.clicked.connect(lambda checked, k=fam_key: self._switch(k))
            sl.addWidget(btn)
            self._cat_btns[fam_key] = btn
        sl.addStretch()
        layout.addWidget(sidebar)

        # ── Colonne gauche : liste + titre ──
        left_col = QVBoxLayout()
        left_col.setContentsMargins(ds.space_md, ds.space_sm, ds.space_xs, ds.space_sm)
        left_col.setSpacing(ds.space_sm)

        self._fam_title = QLabel("")
        self._fam_title.setStyleSheet(f"font-weight: bold; font-size: {s(14)}px; color: {p.text_strong}; border: none;")
        left_col.addWidget(self._fam_title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._cards_w = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_w)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(ds.space_xxs)
        self._scroll.setWidget(self._cards_w)
        left_col.addWidget(self._scroll, 1)

        cancel_btn = QPushButton("Fermer")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(ds.field_height)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.text_strong};
            border: 1px solid {p.outline}; border-radius: {ds.radius_sm}px; }}
            QPushButton:hover {{ background: {p.surface_variant}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        left_col.addWidget(cancel_btn, 0, Qt.AlignRight)

        layout.addLayout(left_col, 1)

        # ── Panneau d'aperçu à droite ──
        preview = QWidget()
        preview.setFixedWidth(ds.sp(SpacingToken.XXXL) * 2)
        preview.setStyleSheet(f"background: {p.surface}; border-left: 1px solid {p.outline_variant};")
        pv = QVBoxLayout(preview)
        pv.setContentsMargins(ds.space_md, ds.space_sm, ds.space_md, ds.space_sm)
        pv.setSpacing(ds.space_sm)

        pv_label = QLabel("Aperçu")
        pv_label.setStyleSheet(f"font-weight: bold; font-size: {s(13)}px; color: {p.text_strong}; border: none;")
        pv.addWidget(pv_label)

        # Header aperçu
        self._pv_code = QLabel("")
        self._pv_code.setFixedWidth(50)
        self._pv_code.setAlignment(Qt.AlignCenter)
        self._pv_code.setStyleSheet(f"font-size: {s(10)}px; font-weight: bold; color: {p.primary}; "
                                     f"background: {p.primary_container}; border-radius: {ds.radius_xs}px; "
                                     f"padding: 2px 6px; border: none;")
        pv_hdr = QHBoxLayout()
        pv_hdr.addWidget(self._pv_code)
        self._pv_title = QLabel("")
        self._pv_title.setWordWrap(True)
        self._pv_title.setStyleSheet(f"font-size: {s(12)}px; font-weight: bold; color: {p.text_strong}; border: none;")
        pv_hdr.addWidget(self._pv_title, 1)
        pv.addLayout(pv_hdr)

        # Corps aperçu
        self._pv_body = QTextEdit()
        self._pv_body.setReadOnly(True)
        self._pv_body.setStyleSheet(f"""
            QTextEdit {{ background: {p.surface}; border: 1px solid {p.outline_variant};
            border-radius: {ds.radius_xs}px; padding: {ds.space_xs}px;
            color: {p.text_strong}; font-size: {s(11)}px; }}
        """)
        pv.addWidget(self._pv_body, 1)

        # Note tokens
        note = QLabel("Les mentions [Nom], [Poste], [Matricule] seront "
                       "remplacées automatiquement à la génération.")
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: {s(9)}px; color: {p.text_soft}; border: none;")
        pv.addWidget(note)

        # Bouton confirmer
        self._confirm_btn = QPushButton("  Sélectionner ce modèle")
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setFixedHeight(ds.field_height)
        self._confirm_btn.setStyleSheet(f"""
            QPushButton {{ background: {p.primary}; color: white; border: none;
            border-radius: {ds.radius_sm}px; padding: {ds.space_xs}px {ds.space_md}px;
            font-size: {s(13)}px; font-weight: bold; }}
            QPushButton:hover {{ background: {p.primary}; }}
            QPushButton:disabled {{ background: {p.outline_variant}; color: {p.text_disabled}; }}
        """)
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._confirm_btn.setEnabled(False)
        pv.addWidget(self._confirm_btn)

        layout.addWidget(preview)
        self.setStyleSheet(self._STYLE)

    # ── Navigation ──

    def _select_first(self):
        if FAMILIES:
            self._switch(FAMILIES[0][0])

    def _switch(self, fam_key: str):
        self._current_family = fam_key
        for k, btn in self._cat_btns.items():
            btn.setChecked(k == fam_key)
        fam_label = next((lbl for k, lbl in FAMILIES if k == fam_key), fam_key)
        self._fam_title.setText(fam_label)
        self._selected_template = None
        self._confirm_btn.setEnabled(False)
        self._populate()

    # ── Cartes + aperçu ──

    def _populate(self):
        while self._cards_layout.count():
            w = self._cards_layout.takeAt(0).widget()
            if w: w.deleteLater()

        p = theme_manager.palette
        s = theme_manager.font_size
        templates = BladoDatabase.get_letter_templates(family=self._current_family, active_only=True)
        builtins = [t for t in templates if t.get("is_builtin")]

        if not builtins:
            self._cards_layout.addWidget(QLabel("Aucun modèle standard dans cette famille."))
            self._cards_layout.addStretch()
            return

        for tpl in builtins:
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            card.setAttribute(Qt.WA_StyledBackground, True)
            card.setStyleSheet(f"""
                QFrame {{ background: {p.surface}; border: 1px solid {p.outline_variant};
                border-radius: {ds.radius_sm}px; }}
                QFrame:hover {{ background: {p.surface_variant}; border-color: {p.primary}; }}
            """)
            crd = QVBoxLayout(card)
            crd.setContentsMargins(ds.space_sm, ds.space_xs, ds.space_sm, ds.space_xs)
            crd.setSpacing(ds.space_xxs)

            r1 = QHBoxLayout()
            code_lbl = QLabel(tpl.get("code", ""))
            code_lbl.setFixedWidth(40)
            code_lbl.setAlignment(Qt.AlignCenter)
            code_lbl.setStyleSheet(f"font-size: {s(11)}px; font-weight: bold; color: {p.primary}; "
                                    f"background: {p.primary_container}; border-radius: {ds.radius_xs}px; "
                                    f"padding: 2px 6px; border: none;")
            r1.addWidget(code_lbl)
            title_lbl = QLabel(tpl.get("title", ""))
            title_lbl.setStyleSheet(f"font-size: {s(13)}px; font-weight: bold; color: {p.text_strong}; border: none;")
            r1.addWidget(title_lbl, 1)
            crd.addLayout(r1)

            desc = tpl.get("description", "")
            if desc:
                d = QLabel(desc)
                d.setWordWrap(True)
                d.setStyleSheet(f"font-size: {s(11)}px; color: {p.text_soft}; border: none; padding-left: 52px;")
                crd.addWidget(d)

            # Clic sur la carte → aperçu
            card.mousePressEvent = lambda e, t=tpl, c=card: self._on_card_click(t, c)
            self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()

    @safe_slot("_CatalogDialog._on_card_click")
    def _on_card_click(self, template: dict, card_widget):
        """Affiche l'aperçu du modèle cliqué."""
        p = theme_manager.palette
        s = theme_manager.font_size
        self._selected_template = template

        # Surbrillance
        for i in range(self._cards_layout.count()):
            w = self._cards_layout.itemAt(i).widget()
            if w and isinstance(w, QFrame):
                w.setStyleSheet(f"""
                    QFrame {{ background: {p.surface}; border: 1px solid {p.outline_variant};
                    border-radius: {ds.radius_sm}px; }}
                    QFrame:hover {{ background: {p.surface_variant}; border-color: {p.primary}; }}
                """)
        card_widget.setStyleSheet(f"""
            QFrame {{ background: {p.surface_variant}; border: 2px solid {p.primary};
            border-radius: {ds.radius_sm}px; }}
        """)

        # Remplir l'aperçu
        code = template.get("code", "")
        self._pv_code.setText(code)
        self._pv_title.setText(template.get("title", ""))
        try:
            body = render_body(PLACEHOLDER_STAFF, code)
            self._pv_body.setPlainText(body)
        except Exception:
            self._pv_body.setPlainText(f"[Erreur lors du rendu du modèle {code}]")

        self._confirm_btn.setEnabled(True)

    @safe_slot("_CatalogDialog._on_confirm")
    def _on_confirm(self):
        if self._selected_template:
            self.template_chosen.emit(self._selected_template)
            self.accept()

    @safe_slot("_CatalogDialog._on_select")
    def _on_select(self, template: dict):
        """Méthode conservée pour rétrocompatibilité — le bouton confirmer est privilégié."""
        self.template_chosen.emit(template)
        self.accept()


# ════════════════════════════════════════════════════════════════════
# Dialogue édition modèle
# ════════════════════════════════════════════════════════════════════

class _EditTemplateDialog(ThemedDialog):
    """Dialogue d'édition d'un modèle entreprise : titre, description, corps."""

    def __init__(self, template: dict, parent=None):
        super().__init__(parent)
        self._template = template
        self._restore_requested = False
        self.setWindowTitle(f"Modifier — {template.get('title', '')}")
        self.setMinimumSize(ds.golden_width(600), ds.golden_height(500))
        self._setup_ui()

    @property
    def _STYLE(self) -> str:
        return f"QDialog {{ background: {theme_manager.palette.surface}; }}"

    @safe_slot("_EditTemplateDialog._restyle")
    def _restyle(self):
        try:
            self.setStyleSheet(self._STYLE)
        except RuntimeError:
            pass

    def _setup_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(ds.space_md, ds.space_md, ds.space_md, ds.space_md)
        layout.setSpacing(ds.space_sm)

        layout.addWidget(QLabel(f"Code : {self._template.get('code', '')}"))

        layout.addWidget(QLabel("Titre :"))
        self._title_edit = QLineEdit(self._template.get("title", ""))
        self._title_edit.setFixedHeight(ds.field_height)
        self._title_edit.setStyleSheet(ds.flat_input_qss())
        layout.addWidget(self._title_edit)

        layout.addWidget(QLabel("Description :"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlainText(self._template.get("description", ""))
        self._desc_edit.setFixedHeight(80)
        self._desc_edit.setStyleSheet(f"""
            QTextEdit {{ background: {p.background}; border: 1px solid {p.outline};
            border-radius: {ds.radius_xs}px; padding: {ds.space_xs}px;
            color: {p.text_strong}; font-size: {s(12)}px; }}
        """)
        layout.addWidget(self._desc_edit)

        # ── Corps du courrier ──
        layout.addWidget(QLabel("Corps du courrier :"))
        # Note sur les tokens auto-remplacés
        note = QLabel("Les mentions [Nom], [Poste], [Matricule] seront "
                       "remplacées automatiquement à la génération.")
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: {s(10)}px; color: {p.text_soft}; border: none;")
        layout.addWidget(note)

        self._body_initial = render_body(
            PLACEHOLDER_STAFF, self._template.get("code", ""),
            template=self._template)

        self._body_edit = QTextEdit()
        self._body_edit.setPlainText(self._body_initial)
        self._body_edit.setMinimumHeight(ds.kpi_card_height * 2)
        self._body_edit.setStyleSheet(f"""
            QTextEdit {{ background: {p.background}; border: 1px solid {p.outline};
            border-radius: {ds.radius_xs}px; padding: {ds.space_sm}px;
            color: {p.text_strong}; font-size: {s(12)}px; }}
            QTextEdit:focus {{ border-color: {p.primary}; }}
        """)
        layout.addWidget(self._body_edit, 1)

        # Bouton restaurer
        restore_btn = QPushButton("  Restaurer le contenu d'origine")
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.setFixedHeight(ds.icon_btn_size + ds.space_xxs)
        restore_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.text_soft};
            border: 1px solid {p.outline}; border-radius: {ds.radius_xs}px;
            padding: 2px {ds.space_xs}px; font-size: {s(11)}px; }}
            QPushButton:hover {{ background: {p.surface_variant}; color: {p.primary}; }}
        """)
        restore_btn.clicked.connect(self._on_restore)
        layout.addWidget(restore_btn)

        # ── Boutons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setFixedHeight(ds.field_height)
        cancel.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.text_strong};
            border: 1px solid {p.outline}; border-radius: {ds.radius_sm}px;
            padding: {ds.space_xs}px {ds.space_md}px; }}
            QPushButton:hover {{ background: {p.surface_variant}; }}
        """)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        save = QPushButton("Enregistrer")
        save.setCursor(Qt.PointingHandCursor)
        save.setFixedHeight(ds.field_height)
        save.setStyleSheet(f"""
            QPushButton {{ background: {p.primary}; color: white; border: none;
            border-radius: {ds.radius_sm}px; padding: {ds.space_xs}px {ds.space_md}px;
            font-weight: bold; }}
            QPushButton:hover {{ background: {p.primary}; }}
        """)
        save.clicked.connect(self.accept)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)
        self.setStyleSheet(self._STYLE)

    @safe_slot("_EditTemplateDialog._on_restore")
    def _on_restore(self):
        """Remet le corps au texte fonction d'origine (body_text = NULL)."""
        original = render_body(
            PLACEHOLDER_STAFF, self._template.get("code", ""),
            template={k: v for k, v in self._template.items() if k != "body_text"})
        self._body_edit.setPlainText(original)
        self._restore_requested = True

    def result(self):
        """Retourne (titre, description, payload) où payload est None,
        {"body_text": ...} ou {"clear_body": True}."""
        payload = None
        if self._restore_requested:
            payload = {"clear_body": True}
        else:
            current = self._body_edit.toPlainText()
            if current != self._body_initial:
                payload = {"body_text": current}
        return self._title_edit.text().strip(), self._desc_edit.toPlainText().strip(), payload


# ════════════════════════════════════════════════════════════════════
# Staff search popup
# ════════════════════════════════════════════════════════════════════

class _StaffSearchPopup(QFrame):
    staff_chosen = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        p = theme_manager.palette
        self.setStyleSheet(f"background: {p.surface}; border: 1px solid {p.outline}; border-radius: {ds.radius_sm}px;")
        self.setMinimumWidth(350)
        self.setMaximumHeight(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._list = QListWidget()
        self._list.setFrameShape(QListWidget.NoFrame)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)
        self._items_data: list[dict] = []

    def set_results(self, results: list[dict]):
        self._items_data = results
        self._list.clear()
        for d in results:
            text = f"{d.get('full_name', '—')}  |  ID {d.get('id', '—')}  |  {d.get('professional_category', '')}"
            self._list.addItem(QListWidgetItem(text))

    @safe_slot("_StaffSearchPopup._on_item_clicked")
    def _on_item_clicked(self, item):
        idx = self._list.row(item)
        if 0 <= idx < len(self._items_data):
            self.staff_chosen.emit(self._items_data[idx])
            self.hide()


# ════════════════════════════════════════════════════════════════════
# LetterManager — page principale
# ════════════════════════════════════════════════════════════════════
