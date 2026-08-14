"""DocumentManager — Gestion des documents employé (label + description + 2 URLs)."""
from __future__ import annotations

import os, shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QLineEdit, QTextEdit, QFrame, QDialog, QFormLayout,
)

from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.icons import icon as md3_icon
from bladocommon.safe_slot import safe_slot

from Blado.common.blado_database import BladoDatabase


class DocumentDialog(QDialog):
    """Dialogue d'ajout/modification d'un document."""

    def __init__(self, staff_id: int, doc: dict | None = None, parent=None):
        super().__init__(parent)
        self._staff_id = staff_id
        self._doc = doc
        self._file_path = doc.get("file_path", "") if doc else ""
        self._supabase_url = doc.get("url", "") if doc else ""

        is_new = doc is None
        self.setWindowTitle("Ajouter un document" if is_new else "Modifier le document")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        layout = QVBoxLayout(self)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_lg, ds.space_lg, ds.space_lg, ds.space_lg)

        form = QFormLayout()
        form.setSpacing(ds.space_sm)

        # Label
        self._label_field = QLineEdit(self._doc.get("label", "") if self._doc else "")
        self._label_field.setPlaceholderText("Ex: Contrat CDI 2026")
        self._label_field.setFixedHeight(ds.field_height)
        self._label_field.setStyleSheet(ds.flat_input_qss())
        form.addRow("Label * :", self._label_field)

        # Description
        self._desc_field = QTextEdit()
        self._desc_field.setPlainText(self._doc.get("description", "") if self._doc else "")
        self._desc_field.setFixedHeight(ds.field_height * 2 + ds.space_xs)
        self._desc_field.setStyleSheet(ds.flat_input_qss())
        form.addRow("Description :", self._desc_field)

        # Fichier local
        file_row = QHBoxLayout()
        file_row.setSpacing(ds.space_sm)
        self._file_label = QLabel(os.path.basename(self._file_path) if self._file_path else "Aucun fichier")
        self._file_label.setStyleSheet(f"color:{p.text_soft};font-size:{s(ds.font_body)}px;border:none;")
        file_row.addWidget(self._file_label, 1)
        browse_btn = QPushButton("Parcourir...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(browse_btn)
        form.addRow("Fichier :", file_row)

        # URL Supabase
        self._url_field = QLineEdit(self._supabase_url)
        self._url_field.setPlaceholderText("https://...supabase.co/...")
        self._url_field.setFixedHeight(ds.field_height)
        self._url_field.setStyleSheet(ds.flat_input_qss())
        form.addRow("URL Supabase :", self._url_field)

        layout.addLayout(form)
        layout.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("Enregistrer")
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(f"background:{p.primary};color:{p.on_primary};font-weight:bold;"
                          f"border:none;border-radius:{ds.radius_sm}px;"
                          f"padding:{ds.space_xs}px {ds.space_md}px;")
        save.clicked.connect(self._on_save)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier", "",
            "Tous (*.pdf *.png *.jpg *.jpeg *.doc *.docx *.xlsx *.txt)")
        if path:
            # Copier dans uploads/<staff_id>/
            upload_dir = os.path.normpath(os.path.join(
                os.path.dirname(__file__), "..", "..", "uploads", str(self._staff_id)))
            os.makedirs(upload_dir, exist_ok=True)
            fname = os.path.basename(path)
            dest = os.path.join(upload_dir, fname)
            shutil.copy2(path, dest)
            self._file_path = dest
            self._file_label.setText(fname)

    def _on_save(self):
        label = self._label_field.text().strip()
        if not label:
            QMessageBox.warning(self, "Champ requis", "Le label est obligatoire.")
            return
        desc = self._desc_field.toPlainText().strip()
        url = self._url_field.text().strip()
        fsize = os.path.getsize(self._file_path) if self._file_path and os.path.isfile(self._file_path) else 0
        BladoDatabase.save_document(self._staff_id, label, desc, self._file_path, url, fsize)
        self.accept()


class DocumentManager(QWidget):
    """Liste des documents d'un employé."""

    def __init__(self, staff_data: dict, parent=None):
        super().__init__(parent)
        self._staff_id = staff_data.get("id", 0)
        self._docs: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        p = theme_manager.palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(ds.space_sm)

        hdr = QHBoxLayout()
        title = QLabel("Documents")
        title.setStyleSheet(f"font-weight:bold;font-size:{theme_manager.font_size(14)}px;color:{p.text_strong};border:none;")
        hdr.addWidget(title)
        hdr.addStretch()

        add_btn = QPushButton("+ Ajouter un document")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"background:{p.primary};color:white;font-weight:bold;border:none;"
                             f"border-radius:{ds.radius_xs}px;padding:{ds.space_xxs}px {ds.space_sm}px;")
        add_btn.clicked.connect(self._on_add)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(ds.space_xs)
        layout.addLayout(self._list_layout)
        layout.addStretch()

    def refresh(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._docs = BladoDatabase.get_documents(self._staff_id) or []
        p = theme_manager.palette
        s = theme_manager.font_size

        if not self._docs:
            empty = QLabel("Aucun document")
            empty.setStyleSheet(f"color:{p.text_soft};font-size:{s(ds.font_body)}px;border:none;")
            self._list_layout.addWidget(empty)
            return

        for doc in self._docs:
            card = QFrame()
            card.setStyleSheet(f"background:{p.surface};border:1px solid {p.outline_variant};"
                              f"border-radius:{ds.radius_sm}px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(ds.space_sm, ds.space_xs, ds.space_sm, ds.space_xs)
            cl.setSpacing(ds.space_xxs)

            # Row 1: Label + size + actions
            r1 = QHBoxLayout()
            r1.setSpacing(ds.space_sm)
            lbl = QLabel(doc["label"])
            lbl.setStyleSheet(f"font-weight:bold;font-size:{s(13)}px;color:{p.text_strong};border:none;")
            r1.addWidget(lbl, 1)
            if doc.get("file_size"):
                sz = doc["file_size"]
                s_str = f"{sz:,} o" if sz < 1024 else f"{sz/1024:.1f} Ko"
                sz_lbl = QLabel(s_str)
                sz_lbl.setStyleSheet(f"font-size:{s(12)}px;color:{p.text_soft};border:none;")
                r1.addWidget(sz_lbl)
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(ds.icon_btn_size, ds.icon_btn_size)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet("QPushButton{border:none;background:transparent;}")
            edit_btn.clicked.connect(lambda checked, d=doc: self._on_edit(d))
            r1.addWidget(edit_btn)
            del_btn = QPushButton("🗑️")
            del_btn.setFixedSize(ds.icon_btn_size, ds.icon_btn_size)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("QPushButton{border:none;background:transparent;}")
            del_btn.clicked.connect(lambda checked, d=doc: self._on_delete(d))
            r1.addWidget(del_btn)
            cl.addLayout(r1)

            # Row 2: Description
            if doc.get("description"):
                desc = QLabel(doc["description"])
                desc.setWordWrap(True)
                desc.setStyleSheet(f"font-size:{s(12)}px;color:{p.text_soft};border:none;")
                cl.addWidget(desc)

            # Row 3: Paths
            if doc.get("file_path"):
                fp = QLabel(f"📁 {doc['file_path']}")
                fp.setStyleSheet(f"font-size:{s(10)}px;color:{p.text_soft};border:none;")
                cl.addWidget(fp)
            if doc.get("url"):
                ul = QLabel(f"🔗 {doc['url']}")
                ul.setStyleSheet(f"font-size:{s(10)}px;color:{p.primary};border:none;")
                cl.addWidget(ul)

            self._list_layout.addWidget(card)

    @safe_slot("DocumentManager._on_add")
    def _on_add(self):
        dlg = DocumentDialog(self._staff_id, parent=self)
        if dlg.exec():
            self.refresh()
            QMessageBox.information(self, "Blado", "Document enregistré.")

    @safe_slot("DocumentManager._on_edit")
    def _on_edit(self, doc: dict):
        dlg = DocumentDialog(self._staff_id, doc, parent=self)
        if dlg.exec():
            self.refresh()
            QMessageBox.information(self, "Blado", "Document modifié.")

    @safe_slot("DocumentManager._on_delete")
    def _on_delete(self, doc: dict):
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer '{doc['label']}' ?")
        if reply == QMessageBox.Yes:
            # Supprimer le fichier local
            if doc.get("file_path") and os.path.isfile(doc["file_path"]):
                try: os.remove(doc["file_path"])
                except OSError: pass
            BladoDatabase.delete_document(doc["id"])
            self.refresh()
