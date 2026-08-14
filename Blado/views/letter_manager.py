"""LetterManager — gestionnaire de courriers et modèles de lettres (Module 12).

Pattern: modèles entreprise (AEC-*) visibles et actionnables, catalogue standard
accessible via "Nouveau modèle" → sélection → duplication automatique.
"""
from __future__ import annotations

import os
from datetime import date

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QLineEdit, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QApplication, QDialog,
)

from bladocommon.session import session
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.icons import icon as md3_icon
from bladocommon.safe_slot import safe_slot
from bladocommon.widgets.themed_widget import ThemedDialog
from phibuilder.phi.scale import SpacingToken

from Blado.common.blado_database import BladoDatabase
from Blado.views.letter_templates import build as build_letter
from Blado.views.letter_templates import generate_docx, render_body, PLACEHOLDER_STAFF
from Blado.views.letter_dialogs import (
    _CatalogDialog, _EditTemplateDialog, _GenerateLetterDialog, _StaffSearchPopup,
    FAMILIES,
)

COMPANY_PREFIX = "AEC-"


def _extract_body_from_full(full_text: str) -> str:
    """Extrait le corps seul d'un texte complet (en-tête + corps + pied)."""
    lines = full_text.split("\n")
    body_start = 0
    footer_start = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("Objet :"):
            body_start = i
        if line == "─" * 60 and i > body_start + 1:
            footer_start = i
            break
    body_lines = lines[body_start + 2:]
    body_only = "\n".join(body_lines).split(f"\n{'─' * 60}\n")[0].strip()
    return body_only


# ════════════════════════════════════════════════════════════════════
# Dialogue de génération
# ════════════════════════════════════════════════════════════════════

class LetterManager(QWidget):
    staff_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_family: str | None = None
        self._selected_staff: dict | None = None
        self._search_text = ""
        self._search_timer: QTimer | None = None
        self._staff_popup: _StaffSearchPopup | None = None
        self._setup_ui()
        self._select_first_family()

    def set_staff(self, staff_data: dict):
        self._selected_staff = staff_data
        if staff_data:
            self._staff_search.setText(f"{staff_data.get('full_name', '')} (ID {staff_data.get('id', '')})")
        self._refresh_cards()

    def _setup_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setFixedWidth(ds.sp(SpacingToken.XXXL) + ds.space_sm * 2)
        sidebar.setAttribute(Qt.WA_StyledBackground, True)
        sidebar.setStyleSheet(f"background: {p.surface_variant}; border-right: 1px solid {p.outline_variant};")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(ds.space_xs, ds.space_sm, ds.space_xs, ds.space_sm)
        sl.setSpacing(ds.space_xxs)

        sl.addWidget(QLabel("Familles"))
        self._cat_buttons: dict[str, QPushButton] = {}
        for fam_key, fam_label in FAMILIES:
            btn = QPushButton(fam_label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(ds.field_height)
            btn.setStyleSheet(f"""
                QPushButton {{ text-align: left; padding: {ds.space_xxs}px {ds.space_xs}px;
                border: none; border-radius: {ds.radius_xs}px; color: {p.text_strong};
                font-size: {s(12)}px; background: transparent; }}
                QPushButton:checked {{ background: {p.primary_container}; color: {p.text_strong}; font-weight: bold; }}
                QPushButton:hover {{ background: {p.surface}; }}
            """)
            btn.clicked.connect(lambda checked, k=fam_key: self._switch_family(k))
            sl.addWidget(btn)
            self._cat_buttons[fam_key] = btn
        sl.addStretch()
        layout.addWidget(sidebar)

        # ── Content ──
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(ds.space_md, ds.space_sm, ds.space_md, ds.space_sm)
        cl.setSpacing(ds.space_sm)

        # Staff selector
        staff_row = QHBoxLayout()
        staff_row.setSpacing(ds.space_sm)
        from phibuilder.widgets import M3TextField
        self._staff_search = M3TextField()
        self._staff_search.setPlaceholderText("Rechercher un employé...")
        self._staff_search.setFixedHeight(ds.field_height)
        self._staff_search.setStyleSheet(ds.flat_input_qss())
        self._staff_search.textChanged.connect(self._on_staff_search_typed)
        staff_row.addWidget(QLabel("Destinataire :"))
        staff_row.addWidget(self._staff_search, 1)
        clear_btn = QPushButton()
        clear_btn.setIcon(md3_icon("close", color=p.text_soft, size=14))
        clear_btn.setFixedSize(ds.icon_btn_size + ds.space_xxs, ds.icon_btn_size + ds.space_xxs)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setToolTip("Effacer")
        clear_btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        clear_btn.clicked.connect(self._clear_staff)
        staff_row.addWidget(clear_btn)
        cl.addLayout(staff_row)

        # Header: titre + bouton Nouveau modèle
        hdr = QHBoxLayout()
        hdr.setSpacing(ds.space_sm)
        self._fam_title = QLabel("")
        self._fam_title.setStyleSheet(f"font-weight: bold; font-size: {s(14)}px; color: {p.text_strong}; border: none;")
        hdr.addWidget(self._fam_title)
        hdr.addStretch()

        new_btn = QPushButton("+ Nouveau modèle")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setFixedHeight(ds.field_height)
        new_btn.setStyleSheet(f"""
            QPushButton {{ background: {p.primary}; color: white; border: none;
            border-radius: {ds.radius_sm}px; padding: {ds.space_xxs}px {ds.space_md}px;
            font-size: {s(13)}px; font-weight: bold; }}
            QPushButton:hover {{ background: {p.primary}; }}
        """)
        new_btn.clicked.connect(self._on_new_model)
        hdr.addWidget(new_btn)
        cl.addLayout(hdr)

        # Compteur
        self._counter_lbl = QLabel("")
        self._counter_lbl.setStyleSheet(f"font-size: {s(12)}px; color: {p.text_soft}; border: none;")
        cl.addWidget(self._counter_lbl)

        # Scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._cards_w = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_w)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(ds.space_xs)
        self._scroll.setWidget(self._cards_w)
        cl.addWidget(self._scroll, 1)
        layout.addWidget(content, 1)

    # ── Staff search ──

    @safe_slot("LetterManager._on_staff_search_typed")
    def _on_staff_search_typed(self, text: str):
        if len(text.strip()) < 2:
            if self._staff_popup: self._staff_popup.hide()
            return
        if self._search_timer is None:
            self._search_timer = QTimer(self); self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._do_staff_search)
        self._search_timer.stop(); self._search_timer.start(300)

    @safe_slot("LetterManager._do_staff_search")
    def _do_staff_search(self):
        q = self._staff_search.text().strip()
        if len(q) < 2: return
        # BLADO multi-clients : la recherche d'employés respecte le client actif
        ent_id = session.entreprise_id if session.mode == "consultant" else None
        filters = {"entreprise_id": ent_id} if ent_id else None
        results = BladoDatabase.search_staff(1001, 5000, is_staff=False,
                                             search_text=q, filters=filters)
        results += BladoDatabase.search_staff(4001, 5000, is_staff=True,
                                              search_text=q, filters=filters)
        seen = set(); unique = []
        for r in results:
            if r["id"] not in seen: seen.add(r["id"]); unique.append(r)
        if unique: self._show_staff_popup(unique[:20])

    def _show_staff_popup(self, results):
        if self._staff_popup is None:
            self._staff_popup = _StaffSearchPopup(self)
            self._staff_popup.staff_chosen.connect(self._on_staff_chosen)
        self._staff_popup.set_results(results)
        self._staff_popup.setFixedWidth(self._staff_search.width())
        pos = self._staff_search.mapToGlobal(self._staff_search.rect().bottomLeft())
        self._staff_popup.move(pos); self._staff_popup.show()

    @safe_slot("LetterManager._on_staff_chosen")
    def _on_staff_chosen(self, staff_data):
        self._selected_staff = staff_data
        self._staff_search.setText(f"{staff_data.get('full_name', '')} (ID {staff_data.get('id', '')})")
        if self._staff_popup: self._staff_popup.hide()
        self._refresh_cards()

    @safe_slot("LetterManager._clear_staff")
    def _clear_staff(self):
        self._selected_staff = None; self._staff_search.clear()
        if self._staff_popup: self._staff_popup.hide()
        self._refresh_cards()

    # ── Navigation ──

    def _select_first_family(self):
        if FAMILIES: self._switch_family(FAMILIES[0][0])

    def _switch_family(self, fam_key: str):
        self._current_family = fam_key
        for k, btn in self._cat_buttons.items(): btn.setChecked(k == fam_key)
        fam_label = next((lbl for k, lbl in FAMILIES if k == fam_key), fam_key)
        self._fam_title.setText(fam_label)
        self._refresh_cards()

    # ── Cards ──

    def _refresh_cards(self):
        while self._cards_layout.count():
            w = self._cards_layout.takeAt(0).widget()
            if w: w.deleteLater()

        p = theme_manager.palette
        s = theme_manager.font_size

        # Affiche UNIQUEMENT les modèles personnalisés (is_builtin=false)
        templates = BladoDatabase.get_letter_templates(family=self._current_family, search=self._search_text)
        customs = [t for t in templates if not t.get("is_builtin")]

        self._counter_lbl.setText(f"{len(customs)} modèle(s) entreprise dans cette famille")

        if not customs:
            empty = QLabel("Aucun modèle entreprise.\nCliquez « + Nouveau modèle » pour ajouter un modèle depuis le catalogue.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {p.text_soft}; font-size: {s(13)}px; border: none; padding: 40px;")
            self._cards_layout.addWidget(empty)
            self._cards_layout.addStretch()
            return

        for tpl in customs:
            card = self._make_card(tpl, p, s)
            self._cards_layout.addWidget(card)
        self._cards_layout.addStretch()

    def _make_card(self, tpl, p, s):
        code = tpl.get("code", "")
        title = tpl.get("title", "")
        desc = tpl.get("description", "")
        family = tpl.get("family", "F")

        card = QFrame()
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QFrame {{ background: {p.surface}; border: 2px solid {p.outline_variant};
            border-radius: {ds.radius_sm}px; }}
            QFrame:hover {{ border-color: {p.primary}; }}
        """)
        crd = QVBoxLayout(card)
        crd.setContentsMargins(ds.space_sm, ds.space_xs, ds.space_sm, ds.space_xs)
        crd.setSpacing(ds.space_xxs)

        # Row 1: code + title + badge AEC
        r1 = QHBoxLayout()
        r1.setSpacing(ds.space_sm)
        code_lbl = QLabel(code)
        code_lbl.setFixedWidth(ds.field_height * 2 + ds.space_xxs)
        code_lbl.setAlignment(Qt.AlignCenter)
        code_lbl.setStyleSheet(f"font-size: {s(10)}px; font-weight: bold; color: white; background: {p.primary}; border-radius: {ds.radius_xs}px; padding: 2px 6px; border: none;")
        r1.addWidget(code_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: {s(13)}px; font-weight: bold; color: {p.text_strong}; border: none;")
        r1.addWidget(title_lbl, 1)

        badge = QLabel("  AEC  ")
        badge.setStyleSheet(f"font-size: {s(8)}px; color: {p.text_strong}; border: 1px solid {p.primary}; border-radius: {ds.space_xxs}px; padding: 1px 4px; background: {p.primary_container};")
        r1.addWidget(badge)
        crd.addLayout(r1)

        if desc:
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet(f"font-size: {s(12)}px; color: {p.text_soft}; border: none; padding-left: {ds.field_height * 2 + ds.space_xxs + ds.space_sm}px;")
            crd.addWidget(d)

        # Famille
        fam_names = {"A": "Contrat", "B": "Rémunération", "C": "Discipline", "D": "Congé",
                     "E": "Départ", "F": "Vie pro", "G": "Recrutement", "H": "Demande employé",
                     "I": "IB", "J": "Syndical"}
        fam_lbl = QLabel(fam_names.get(family, ""))
        fam_lbl.setStyleSheet(f"font-size: {s(10)}px; color: {p.text_soft}; border: none; padding-left: {ds.field_height * 2 + ds.space_xxs + ds.space_sm}px;")
        crd.addWidget(fam_lbl)

        # Staff chip
        actions = QHBoxLayout()
        actions.setSpacing(ds.space_xxs)
        if self._selected_staff:
            chip = QLabel(f"  {self._selected_staff.get('full_name', '')[:25]}  ")
            chip.setStyleSheet(f"font-size: {s(10)}px; color: {p.text_strong}; background: {p.primary_container}; border-radius: {ds.radius_sm}px; padding: 2px 6px; border: none;")
            chip.setFixedHeight(ds.space_m3)
            actions.addWidget(chip)
        else:
            actions.addWidget(QLabel("  Pas de destinataire  "))
        actions.addStretch()

        # Modifier
        edit_btn = QPushButton("  Modifier")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedHeight(ds.icon_btn_size + ds.space_xxs)
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.text_soft};
            border: 1px solid {p.outline}; border-radius: {ds.radius_xs}px;
            padding: 2px {ds.space_xs}px; font-size: {s(12)}px; }}
            QPushButton:hover {{ background: {p.surface_variant}; color: {p.text_strong}; }}
        """)
        edit_btn.clicked.connect(lambda checked, t=tpl: self._on_edit(t))
        actions.addWidget(edit_btn)

        # Supprimer
        del_btn = QPushButton("  Supprimer")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedHeight(ds.icon_btn_size + ds.space_xxs)
        del_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {p.error};
            border: 1px solid {p.error}; border-radius: {ds.radius_xs}px;
            padding: 2px {ds.space_xs}px; font-size: {s(12)}px; }}
            QPushButton:hover {{ background: {p.error}; color: white; }}
        """)
        del_btn.clicked.connect(lambda checked, t=tpl: self._on_delete(t))
        actions.addWidget(del_btn)

        # Générer
        gen_btn = QPushButton("  Générer")
        gen_btn.setCursor(Qt.PointingHandCursor)
        gen_btn.setFixedHeight(ds.icon_btn_size + ds.space_xxs)
        gen_btn.setStyleSheet(f"""
            QPushButton {{ background: {p.primary}; color: white; border: none;
            border-radius: {ds.radius_xs}px; padding: 2px {ds.space_xs}px;
            font-size: {s(12)}px; font-weight: bold; }}
            QPushButton:hover {{ background: {p.primary}; }}
        """)
        gen_btn.clicked.connect(lambda checked, t=tpl: self._on_generate(t))
        actions.addWidget(gen_btn)
        crd.addLayout(actions)

        return card

    # ── Actions ──

    @safe_slot("LetterManager._on_new_model")
    def _on_new_model(self):
        dlg = _CatalogDialog(self)
        dlg.template_chosen.connect(self._on_template_chosen)
        # no-popup-feedback : simple sélecteur — le message d'action est émis
        # par _on_template_chosen au choix du modèle.
        dlg.exec()

    @safe_slot("LetterManager._on_template_chosen")
    def _on_template_chosen(self, template: dict):
        """Duplique un standard en modèle entreprise."""
        new_code = f"{COMPANY_PREFIX}{template.get('code', '')}"
        existing = BladoDatabase.get_letter_templates(search=new_code)
        if existing:
            QMessageBox.information(self, "Déjà existant",
                f"Un modèle {new_code} existe déjà. Modifiez-le directement.")
            return
        new_id = BladoDatabase.save_letter_template({
            "family": template.get("family", "F"),
            "code": new_code,
            "title": f"{COMPANY_PREFIX}{template.get('title', '')}",
            "description": f"[De {template.get('code', '')}] {template.get('description', '')}",
            "source_code": template.get("code", ""),
            "created_by": session.user_id,
        })
        if new_id:
            # Aller sur la famille correspondante
            fam = template.get("family", "F")
            if fam in self._cat_buttons:
                self._switch_family(fam)
            QMessageBox.information(self, "Modèle ajouté",
                f"Le modèle {new_code} est maintenant dans vos modèles entreprise.\n"
                f"Vous pouvez le modifier avant de générer un courrier.")
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de créer le modèle.")

    @safe_slot("LetterManager._on_edit")
    def _on_edit(self, template: dict):
        dlg = _EditTemplateDialog(template, parent=self)
        if dlg.exec():
            new_title, new_desc, payload = dlg.result()
            if new_title:
                data = {"id": template["id"], "title": new_title, "description": new_desc}
                if payload:
                    data.update(payload)
                BladoDatabase.save_letter_template(data)
                self._refresh_cards()
                QMessageBox.information(self, "Blado", "Modèle enregistré.")

    @safe_slot("LetterManager._on_delete")
    def _on_delete(self, template: dict):
        code = template.get("code", "")
        r = QMessageBox.question(self, "Supprimer",
            f"Supprimer définitivement le modèle {code} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            BladoDatabase.toggle_letter_template(template["id"], False)
            self._refresh_cards()

    @safe_slot("LetterManager._on_generate")
    def _on_generate(self, template: dict):
        Service = None
        if self._selected_staff:
            cid = self._selected_staff.get("fk_service_id")
            if cid: Service = BladoDatabase.get_service_full(cid)
        dlg = _GenerateLetterDialog(template, self._selected_staff, Service=Service, parent=self)
        # no-popup-feedback : le dialogue de génération affiche son propre
        # message « Courrier généré » avant de se fermer.
        dlg.exec()

    def refresh(self):
        self._refresh_cards()