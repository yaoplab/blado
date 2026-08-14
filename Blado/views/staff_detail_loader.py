# StaffDetailLoaderMixin — méthodes _load_* extraites de StaffDetail
# BLADO: fichier ≤ 1000 lignes (règle pyside6-wrapper)

from __future__ import annotations
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
from bladocommon.database import db
from bladocommon.design_system import ds
from bladocommon.safe_slot import safe_slot
from bladocommon.theme import theme_manager
from Blado.common.blado_database import BladoDatabase

class StaffDetailLoaderMixin:
    def _load_personal(self):
        d = self._full or {}
        layout = self._personal_layout

        # --- Identité ---
        card1, body1 = self._info_card("Identité", "person",
                                       action_label="Modifier",
                                       action_slot=self._on_edit_identity)
        grid1 = QGridLayout()
        grid1.setSpacing(ds.space_sm)
        for i in range(3):
            grid1.setColumnStretch(i, 1)

        id_vals = [
            ("Civilité", d.get("civility")),
            ("Nationalité", d.get("nationality")),
            ("Situation familiale", d.get("marital_status")),
            ("Enfants à charge", d.get("children_count", 0)),
            ("Groupe sanguin", d.get("blood_type")),
            ("Pièce d'identité",
             f"{d.get('id_document_type','')} {d.get('id_document_number','')}".strip()),
            ("Expiration pièce ID", d.get("id_document_expiry")),
        ]
        for col, (lbl, val) in enumerate(id_vals):
            row, c = divmod(col, 3)
            grid1.addLayout(self._field_cell(lbl, val or "—"), row, c)
        body1.addLayout(grid1)
        layout.addWidget(card1)

        # --- Contact ---
        card2, body2 = self._info_card("Contact", "mail")
        grid2 = QGridLayout()
        grid2.setSpacing(ds.space_sm)
        for i in range(2):
            grid2.setColumnStretch(i, 1)

        ct_vals = [
            ("Email professionnel", d.get("email")),
            ("Email personnel", d.get("personal_email")),
            ("Téléphone fixe", d.get("phone_home")),
            ("Téléphone portable", d.get("phone_mobile")),
            ("Contact d'urgence", d.get("emergency_contact_name")),
            ("Téléphone urgence", d.get("emergency_contact_phone")),
        ]
        for col, (lbl, val) in enumerate(ct_vals):
            row, c = divmod(col, 2)
            grid2.addLayout(self._field_cell(lbl, val or "—"), row, c)
        body2.addLayout(grid2)
        layout.addWidget(card2)

        # --- Professionnel ---
        card3, body3 = self._info_card("Professionnel", "work")
        grid3 = QGridLayout()
        grid3.setSpacing(ds.space_sm)
        for i in range(3):
            grid3.setColumnStretch(i, 1)

        pro_vals = [
            ("Matricule", d.get("matricule")),
            ("Catégorie pro.", d.get("professional_category")),
            ("Statut", d.get("emp_status")),
            ("Date d'embauche", d.get("hire_date")),
            ("N° CNSS", d.get("cnss_number")),
            ("N° fiscal", d.get("tax_id")),
        ]
        for col, (lbl, val) in enumerate(pro_vals):
            row, c = divmod(col, 3)
            grid3.addLayout(self._field_cell(lbl, val or "—"), row, c)
        body3.addLayout(grid3)
        layout.addWidget(card3)

        self._add_stretch(layout)

    # ── Page 1 : Diplômes & Langues ──

    def _load_degrees(self):
        layout = self._degrees_layout
        p = theme_manager.palette
        s = theme_manager.font_size

        card, body = self._info_card("Diplômes & Langues", "school",
                                     action_label="Ajouter",
                                     action_slot=self._on_edit_degrees)

        cols = QHBoxLayout()
        cols.setSpacing(ds.space_md)

        # Diplômes
        deg_col = QVBoxLayout()
        deg_col.setSpacing(ds.space_xxs)
        deg_title = QLabel("Diplômes")
        deg_title.setStyleSheet(
            f"font-size: {s(13)}px; font-weight: bold; color: {p.text_soft}; border: none;")
        deg_col.addWidget(deg_title)

        degrees = BladoDatabase.get_degrees(self._staff.get("id", 0))
        if not degrees:
            deg_col.addWidget(self._empty_label("Aucun diplôme"))
        else:
            for deg in degrees:
                text = f"{deg['degree_type']} — {deg.get('institution','')} ({deg.get('year_obtained','')})"
                item = QLabel(text)
                item.setWordWrap(True)
                item.setStyleSheet(
                    f"font-size: {s(12)}px; color: {p.text_strong}; border: none;")
                deg_col.addWidget(item)
        deg_col.addStretch()
        cols.addLayout(deg_col, 1)

        # Langues
        lang_col = QVBoxLayout()
        lang_col.setSpacing(ds.space_xxs)
        lang_title = QLabel("Langues")
        lang_title.setStyleSheet(
            f"font-size: {s(13)}px; font-weight: bold; color: {p.text_soft}; border: none;")
        lang_col.addWidget(lang_title)

        languages = BladoDatabase.get_languages(self._staff.get("id", 0))
        if not languages:
            lang_col.addWidget(self._empty_label("Aucune langue"))
        else:
            for lang in languages:
                text = f"{lang['language']} — {lang.get('proficiency','')}"
                item = QLabel(text)
                item.setStyleSheet(
                    f"font-size: {s(12)}px; color: {p.text_strong}; border: none;")
                lang_col.addWidget(item)
        lang_col.addStretch()
        cols.addLayout(lang_col, 1)

        body.addLayout(cols)
        layout.addWidget(card)
        self._add_stretch(layout)

    # ── Page 4 : Contrats ──

    def _load_contracts(self):
        from Blado.views.contract_list import ContractList
        layout = self._contracts_layout
        self._contract_widget = ContractList(self._staff, parent=self)
        layout.addWidget(self._contract_widget, 1)

    @safe_slot("StaffDetail._on_add_contract")
    def _on_add_contract(self):
        from Blado.views.contract_form import ContractFormDialog
        dlg = ContractFormDialog(self._staff.get("id", 0), parent=self)
        if dlg.exec() and hasattr(self, "_contract_widget"):
            self._contract_widget.refresh()
            QMessageBox.information(self, "Blado", "Contrat enregistré.")

    # ── Page 5 : Congés ──

    def _load_leave(self):
        from Blado.views.leave_balance import LeaveBalanceWidget, LeaveRequestHistory
        layout = self._leave_layout

        self._leave_balance = LeaveBalanceWidget(self._staff, parent=self)
        layout.addWidget(self._leave_balance)

        self._leave_history = LeaveRequestHistory(self._staff, parent=self)
        self._leave_history.leave_validated.connect(
            lambda: self._leave_balance.refresh() if hasattr(self, "_leave_balance") else None)
        layout.addWidget(self._leave_history, 1)

    @safe_slot("StaffDetail._on_add_leave")
    def _on_add_leave(self):
        from Blado.views.leave_request import LeaveRequestDialog
        dlg = LeaveRequestDialog(self._staff.get("id", 0), parent=self)
        if dlg.exec():
            if hasattr(self, "_leave_balance"):
                self._leave_balance.refresh()
            if hasattr(self, "_leave_history"):
                self._leave_history.refresh()
            QMessageBox.information(self, "Blado", "Demande de congé enregistrée.")

    # ── Page 6 : Documents ──

    def _load_documents(self):
        from Blado.views.document_manager import DocumentManager
        layout = self._documents_layout

        self._doc_manager = DocumentManager(self._staff, parent=self)
        layout.addWidget(self._doc_manager, 1)

    # ── Page 6 : Courriers ──

    def _load_letters(self):
        from Blado.views.letter_manager import LetterManager
        layout = self._letters_layout

        self._letter_manager = LetterManager(parent=self)
        self._letter_manager.set_staff(self._staff)
        self._letter_manager.setMinimumHeight(ds.workspace_min_height * 3 + ds.space_xxl)
        layout.addWidget(self._letter_manager, 1)

    # ── Page 7 : Événements ──

    def _load_events(self):
        """Page Evenements — 2 tableaux (absences + retards) avec edition inline."""
        layout = self._events_layout
        p = theme_manager.palette
        s = theme_manager.font_size

        conn = db.server_conn
        if not conn:
            layout.addWidget(self._empty_label("Base de donnees indisponible"))
            self._add_stretch(layout)
            return

        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT event_id, event_type, COALESCE(event_at, created_at) AS evt_at,
                       note
                FROM blado_event WHERE staff_id = %s
                ORDER BY event_at DESC LIMIT 200
            """, (self._staff["id"],))
            all_rows = cur.fetchall()

            absences = [r for r in all_rows if r[1] and r[1].startswith("Absence")]
            retards  = [r for r in all_rows if r[1] and r[1].startswith("Retard")]

            if not all_rows:
                layout.addWidget(self._empty_label("Aucun evenement enregistre"))
                self._add_stretch(layout)
                return

            # ── ABSENCES ──
            abs_lbl = QLabel("Absences")
            abs_lbl.setStyleSheet(
                f"font-size: {s(13)}px; font-weight: bold; color: {p.error}; "
                f"border: none; padding-left: {ds.space_xs}px;")
            layout.addWidget(abs_lbl)
            layout.addWidget(self._build_event_table(absences, p.error))

            layout.addSpacing(ds.space_md)

            # ── RETARDS ──
            ret_lbl = QLabel("Retards")
            ret_lbl.setStyleSheet(
                f"font-size: {s(13)}px; font-weight: bold; color: {p.tertiary}; "
                f"border: none; padding-left: {ds.space_xs}px;")
            layout.addWidget(ret_lbl)
            layout.addWidget(self._build_event_table(retards, p.tertiary))

        except Exception:
            import traceback
            traceback.print_exc()
            layout.addWidget(self._empty_label("Erreur de chargement"))

        self._add_stretch(layout)
