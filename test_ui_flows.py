#!/usr/bin/env python3
"""Blado — Tests de flux UI complets (offscreen, données __TESTFLOW__).

Usage:
  python test_ui_flows.py            # déroule tous les flux (la base est remplie)
  python test_ui_flows.py --cleanup  # supprime les données de test + artefacts

Ce script pilote la VRAIE interface : chaque dialogue est instancié, rempli
avec des données factices, et son bouton Enregistrer est réellement cliqué.
Les boîtes modales (QMessageBox/QFileDialog/QColorDialog) sont auto-répondues
pour ne jamais bloquer. Toutes les écritures en base sont vérifiées ensuite.

Les données de test sont préfixées __TESTFLOW__ pour un nettoyage facile.
"""
import os
import shutil
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "BladoCommon"))

from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QMessageBox, QFileDialog, QColorDialog,
    QLineEdit, QComboBox, QCheckBox, QTextEdit, QDateEdit,
    QSpinBox, QDoubleSpinBox,
)

# ── Auto-réponses des boîtes modales ────────────────────────────────────────
MSGS: list[tuple[str, str]] = []


def _patched_box(parent, title, text, *a, **k):
    MSGS.append((str(title), str(text)))
    return QMessageBox.Ok


def _patched_question(parent, title, text, *a, **k):
    MSGS.append((str(title), str(text)))
    return QMessageBox.Yes


QMessageBox.information = staticmethod(_patched_box)
QMessageBox.warning = staticmethod(_patched_box)
QMessageBox.critical = staticmethod(_patched_box)
QMessageBox.question = staticmethod(_patched_question)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
_TEST_OUT_DIR = os.path.join(ROOT, "uploads", "_testflow")
os.makedirs(_TEST_OUT_DIR, exist_ok=True)
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (os.path.join(_TEST_OUT_DIR, "courrier_test.docx"), ""))
QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#2E7D32"))

# ── Auto-exec des dialogues : chaque exec() exécute d'abord le handler
# enregistré pour cette classe (remplissage + clic réel), puis renvoie
# Accepted — les boutons des pages qui ouvrent des dialogues deviennent
# testables sans boucle d'événements bloquante.
from PySide6.QtWidgets import QDialog

_DIALOG_HANDLERS: dict = {}


def _auto_exec(self):
    handler = None
    for cls in type(self).__mro__:
        if cls in _DIALOG_HANDLERS:
            handler = _DIALOG_HANDLERS[cls]
            break
    if handler:
        try:
            handler(self)
        except Exception:
            import traceback
            traceback.print_exc()
            return QDialog.Rejected
    return QDialog.Accepted


QDialog.exec = _auto_exec

MARK = "__TESTFLOW__"
FAILURES = 0
CHECKS = 0


def check(label: str, ok_: bool, detail: str = ""):
    global FAILURES, CHECKS
    CHECKS += 1
    if ok_:
        print(f"✅ {label}")
    else:
        FAILURES += 1
        print(f"❌ {label}" + (f" — {detail}" if detail else ""))


def flow(label: str, fn):
    """Exécute un flux ; toute exception = échec détaillé avec traceback."""
    try:
        fn()
    except Exception as ex:
        import traceback
        global FAILURES, CHECKS
        CHECKS += 1
        FAILURES += 1
        tb = traceback.format_exc().strip().splitlines()
        origin = next((l.strip() for l in reversed(tb) if l.strip().startswith("File")), "")
        print(f"❌ {label} — {type(ex).__name__}: {ex}")
        print(f"   {origin}")
        print("   " + tb[-1].strip())


def _fill(dlg, **fields):
    """Remplit les champs d'un dialogue par nom d'attribut."""
    for name, val in fields.items():
        w = getattr(dlg, name)
        if isinstance(w, QLineEdit):
            w.setText(str(val))
        elif isinstance(w, QComboBox):
            if isinstance(val, int):
                w.setCurrentIndex(val)
            elif isinstance(val, str):
                idx = w.findText(val)
                if idx >= 0:
                    w.setCurrentIndex(idx)
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(val))
        elif isinstance(w, QTextEdit):
            w.setPlainText(str(val))
        elif isinstance(w, QDateEdit):
            w.setDate(val if isinstance(val, QDate) else QDate.fromString(str(val), "yyyy-MM-dd"))
        elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
            w.setValue(val)
        else:
            raise TypeError(f"{name}: {type(w).__name__} non pris en charge")


def _query(sql, params=()):
    cur = _conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


# ── Environnement ───────────────────────────────────────────────────────────
_app = QApplication.instance() or QApplication([])
from bladocommon.database import db
from bladocommon.theme import theme_manager
from bladocommon.session import session
from Blado.common.blado_database import BladoDatabase

assert db.connect_intranet(), "Connexion DB impossible"
_conn = db.server_conn
theme_manager.bind(_app)
session.mode = "consultant"

# IDs créés pendant les tests (pour le rapport et le nettoyage)
CREATED = {"employees": [], "templates": [], "missions": [], "services_activated": [],
           "service_ent_restore": {}}


# ═══════════════════════════════════════════════════════════════════════════
# 1. Employé — création (mode rapide) puis vérification base
# ═══════════════════════════════════════════════════════════════════════════
def t1_create_employee():
    from Blado.views.staff_form import StaffFormDialog
    slots = []
    for svc in BladoDatabase.get_services():
        if svc.get("enabled"):
            slots = BladoDatabase.get_free_slots(svc["id"])
            if slots:
                break
    assert slots, "aucun slot libre trouvé"
    dlg = StaffFormDialog(0, 0, slot_id=slots[0]["id"])
    _fill(dlg, _f_first_name="UIFlow", _f_last_name=f"{MARK}Alpha")
    dlg._on_quick_save()
    check("Employé créé (mode rapide)", dlg._new_id is not None)
    CREATED["employees"].append(dlg._new_id)
    rows = _query(
        "SELECT first_name, last_name, is_active, emp_status FROM blado_employee WHERE id=%s",
        (dlg._new_id,))
    check("Employé présent en base (actif)", bool(rows) and rows[0][2] is True and rows[0][3] == "actif",
          str(rows))
    dlg.deleteLater()
    return dlg._new_id


# ═══════════════════════════════════════════════════════════════════════════
# 2. Employé — édition complète (toutes sections) + vérification base
# ═══════════════════════════════════════════════════════════════════════════
def t2_edit_employee(emp_id):
    from Blado.views.staff_form import StaffFormDialog
    full = BladoDatabase.get_staff_full(emp_id)
    assert full, "get_staff_full a échoué"
    dlg = StaffFormDialog(0, 0, staff_data=full)
    _fill(dlg,
          _f_cnss="TST123456", _f_matricule="TST-9001",
          _f_tel_mobile="+228 90 12 34 56", _f_blood="O+",
          _f_id_number="TSTID999", _f_nationality="Togolaise")
    dlg._on_save()
    rows = _query(
        "SELECT cnss_number, matricule, phone_mobile, blood_type FROM blado_employee WHERE id=%s",
        (emp_id,))
    ok_ = bool(rows) and rows[0][0] == "TST123456" and rows[0][1] == "TST-9001" \
        and rows[0][2] == "+228 90 12 34 56" and rows[0][3] == "O+"
    check("Édition complète enregistrée en base", ok_, str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Fiche employé — navigation dans toutes les sections
# ═══════════════════════════════════════════════════════════════════════════
def t3_staff_detail(emp_id):
    from Blado.views.staff_detail import StaffDetail
    staff = BladoDatabase.search_staff(0, 0, False, f"{MARK}Alpha", {})
    assert staff, "employé introuvable via search_staff"
    detail = StaffDetail(staff[0], on_back=lambda: None)
    for i in range(len(detail._categories)):
        detail._switch_category(i)
        _app.processEvents()
    check("Fiche employé — toutes les sections navigables", True)
    detail.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 4. Contrat — création via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t4_contract(emp_id):
    from Blado.views.contract_form import ContractFormDialog
    dlg = ContractFormDialog(emp_id)
    _fill(dlg, _f_salary="250000", _f_hours="40", _f_class="Ouvrier", _f_echelon="3")
    dlg._on_save()
    rows = _query(
        "SELECT contract_type, salaire_brut, volume_horaire, statut FROM blado_contract WHERE staff_id=%s",
        (emp_id,))
    check("Contrat créé en base", bool(rows) and rows[0][3] == "actif", str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 5. Congé — demande via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t5_leave(emp_id):
    from Blado.views.leave_request import LeaveRequestDialog
    dlg = LeaveRequestDialog(emp_id)
    _fill(dlg, _f_motif="Test flux UI")
    dlg._on_save()
    rows = _query(
        "SELECT leave_type, nb_days, status FROM blado_leave_request WHERE staff_id=%s",
        (emp_id,))
    check("Demande de congé créée en base", bool(rows) and rows[0][2] == "en_attente", str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 6. Événement (absence) via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t6_event(emp_id):
    from Blado.views.staff_events import StaffEventDialog
    # Cibler l'employé du run courant par id (search_staff renvoie le premier
    # __TESTFLOW__Alpha des runs précédents → faux échec "0 → 0")
    staff = BladoDatabase.get_staff_full(emp_id)
    assert staff, f"employé de test {emp_id} introuvable"
    before = _query("SELECT COUNT(*) FROM blado_event WHERE staff_id=%s", (emp_id,))[0][0]
    dlg = StaffEventDialog(staff)
    dlg._select_mode("Ab")
    dlg._motif_field.setCurrentIndex(0)
    dlg._note.setPlainText("Absence test flux UI")
    dlg._on_save()
    after = _query("SELECT COUNT(*) FROM blado_event WHERE staff_id=%s", (emp_id,))[0][0]
    check("Événement absence créé en base", after == before + 1, f"{before} → {after}")
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 7. Document via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t7_document(emp_id):
    from Blado.views.document_manager import DocumentDialog
    dlg = DocumentDialog(emp_id)
    _fill(dlg, _label_field=f"{MARK}Doc", _desc_field="Document test flux UI")
    dlg._on_save()
    rows = _query("SELECT label FROM blado_document WHERE staff_id=%s AND label=%s",
                  (emp_id, f"{MARK}Doc"))
    check("Document créé en base", bool(rows), str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 8. Mission via le dialogue réel (consultant ERIDD + client Steel Togo)
# ═══════════════════════════════════════════════════════════════════════════
def t8_mission():
    from Blado.views.mission_dialog import MissionDialog
    phi = theme_manager.phi_theme
    dlg = MissionDialog(phi)
    _fill(dlg, _f_ref=f"{MARK}001", _f_titre="Mission test flux UI",
          _f_montant=100000)
    dlg.accept()
    new_id = BladoDatabase.save_mission(dlg.get_data())
    check("Mission enregistrée en base", new_id is not None)
    CREATED["missions"].append(new_id)
    rows = _query("SELECT reference, statut FROM missions WHERE id=%s", (new_id,))
    check("Mission vérifiée (référence TESTFLOW)", bool(rows) and rows[0][0] == f"{MARK}001",
          str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 9. Consultant (cabinet) via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t9_consultant():
    from Blado.views.settings_page import ConsultantDialog
    phi = theme_manager.phi_theme
    dlg = ConsultantDialog(phi)
    _fill(dlg, _f_nom=f"{MARK}Cabinet", _f_sigle="TF", _f_email="test@testflow.tg")
    dlg._on_save()
    new_id = BladoDatabase.save_consultant(dlg.get_data())
    check("Consultant enregistré en base", new_id is not None)
    rows = _query("SELECT nom FROM consultants WHERE id=%s", (new_id,))
    check("Consultant vérifié", bool(rows) and rows[0][0] == f"{MARK}Cabinet", str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 10. Entreprise cliente via le dialogue réel
# ═══════════════════════════════════════════════════════════════════════════
def t10_entreprise():
    from Blado.views.settings_page import EntrepriseDialog
    phi = theme_manager.phi_theme
    dlg = EntrepriseDialog(phi)
    _fill(dlg, _f_nom=f"{MARK}Client", _f_sigle="TFC", _f_ville="Lomé")
    dlg._on_save()
    new_id = BladoDatabase.save_entreprise(dlg.get_data())
    check("Entreprise cliente enregistrée en base", new_id is not None)
    rows = _query("SELECT nom FROM entreprises WHERE id=%s", (new_id,))
    check("Entreprise vérifiée", bool(rows) and rows[0][0] == f"{MARK}Client", str(rows))
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 11. Service — rattachement client + héritage employé + activation
# ═══════════════════════════════════════════════════════════════════════════
def t11_service(emp_id):
    from Blado.views.service_page import ServiceDialog
    phi = theme_manager.phi_theme
    # Rattacher Steel Togo (id 1) au service de l'employé de test
    svc_id = _query("SELECT fk_service_id FROM blado_employee WHERE id=%s", (emp_id,))[0][0]
    old_ent = _query("SELECT entreprise_id FROM services WHERE id=%s", (svc_id,))[0][0]
    CREATED["service_ent_restore"][svc_id] = old_ent
    svc = next(s for s in BladoDatabase.get_services() if s["id"] == svc_id)
    dlg = ServiceDialog(phi, svc)
    idx = dlg._client_combo.findData(1)
    dlg._client_combo.setCurrentIndex(idx if idx >= 0 else 0)
    dlg.accept()
    BladoDatabase.create_service(dlg.get_data())
    ent = _query("SELECT fk_entreprise_id FROM blado_employee WHERE id=%s", (emp_id,))[0][0]
    check("Employé hérite du client du service (fk_entreprise_id=1)", ent == 1, f"ent={ent}")
    dlg.deleteLater()
    # Activer un service désactivé (flux « + Activer un service »)
    disabled = BladoDatabase.get_first_disabled_service()
    if disabled:
        dlg2 = ServiceDialog(phi, disabled)
        dlg2.accept()
        data = dlg2.get_data()
        BladoDatabase.create_service(data)
        if data.get("enabled"):
            BladoDatabase.create_service_gabarit(data["id"], 99)
        CREATED["services_activated"].append(data["id"])
        check("Service activé via le dialogue",
              _query("SELECT enabled FROM services WHERE id=%s", (data["id"],))[0][0] is True)
        dlg2.deleteLater()
    else:
        print("ℹ️  Aucun service désactivé à activer — test ignoré")


# ═══════════════════════════════════════════════════════════════════════════
# 12. Paie — lancement réel du mois courant
# ═══════════════════════════════════════════════════════════════════════════
def t12_payroll(emp_id):
    from Blado.views.payslip_run import PayslipRunPage
    page = PayslipRunPage()
    month = page._month_combo.currentData()
    year = page._year_combo.currentData()
    page._on_run()
    rows = _query(
        "SELECT COUNT(*) FROM blado_payslip WHERE period_month=%s AND period_year=%s",
        (month, year))
    check("Paie générée (bulletins en base)", rows[0][0] > 0, f"{rows[0][0]} bulletins")
    mine = _query(
        "SELECT COUNT(*) FROM blado_payslip WHERE employee_id=%s AND period_month=%s AND period_year=%s",
        (emp_id, month, year))
    check("Bulletin de l'employé de test généré", mine[0][0] > 0, str(mine[0][0]))
    page.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 13. Courriers — modèle entreprise + génération réelle d'un courrier
# ═══════════════════════════════════════════════════════════════════════════
def t13_letters(emp_id):
    from Blado.views.letter_dialogs import _EditTemplateDialog, _GenerateLetterDialog
    tpl_id = BladoDatabase.save_letter_template({
        "family": "F", "code": "TSTF001", "title": f"{MARK}Modèle",
        "description": "Modèle test flux UI", "created_by": session.user_id,
    })
    check("Modèle de courrier créé", tpl_id is not None)
    CREATED["templates"].append(tpl_id)
    tpl = BladoDatabase.get_letter_template_by_id(tpl_id)
    dlg = _EditTemplateDialog(tpl)
    _fill(dlg, _title_edit=f"{MARK}Modèle modifié")
    title, desc, payload = dlg.result()
    BladoDatabase.save_letter_template({"id": tpl_id, "title": title, "description": desc})
    rows = _query("SELECT title FROM blado_letter_template WHERE id=%s", (tpl_id,))
    check("Modèle modifié via le dialogue", bool(rows) and rows[0][0] == f"{MARK}Modèle modifié",
          str(rows))
    dlg.deleteLater()
    # Génération réelle (docx + enregistrement)
    staff = BladoDatabase.search_staff(0, 0, False, f"{MARK}Alpha", {})[0]
    gdlg = _GenerateLetterDialog(tpl, staff)
    gdlg._objet_field.setText("Objet test flux UI")
    gdlg._on_generate()
    ok_gen = bool(gdlg._output_path) and os.path.isfile(gdlg._output_path)
    check("Courrier généré (fichier créé)", ok_gen, gdlg._output_path or "aucun chemin")
    rows = _query(
        "SELECT COUNT(*) FROM blado_generated_letter g "
        "JOIN blado_letter_template t ON t.id=g.template_id WHERE t.code=%s",
        ("TSTF001",))
    check("Courrier enregistré en base", rows[0][0] > 0, str(rows[0][0]))
    gdlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 14. Validation — nom obligatoire bloqué par le dialogue
# ═══════════════════════════════════════════════════════════════════════════
def t14_validation():
    from Blado.views.settings_page import ConsultantDialog
    from PySide6.QtWidgets import QDialog
    phi = theme_manager.phi_theme
    n_msgs = len(MSGS)
    dlg = ConsultantDialog(phi)
    dlg._f_nom.setText("")
    dlg._on_save()
    check("Validation nom vide → refus + message",
          dlg.result() != QDialog.Accepted and len(MSGS) > n_msgs,
          f"result={dlg.result()}, msgs+{len(MSGS) - n_msgs}")
    dlg.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# 15. Thèmes — changement complet sans crash
# ═══════════════════════════════════════════════════════════════════════════
def t15_themes():
    from Blado.views.main_window import MainWindow
    mw = MainWindow()
    mw._switch_to("dashboard")
    for tname in theme_manager.names():
        key = tname[0]
        theme_manager.set_active(key)
        mw._restyle()
        _app.processEvents()
    check("Changement de thème sur la fenêtre principale (tous thèmes)", True)
    mw.close(); mw.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# PARTIE 2 — Clics RÉELS sur les boutons des pages (ouverts via exec() auto)
# ═══════════════════════════════════════════════════════════════════════════
def _click_button(widget, text_or_tip):
    from PySide6.QtWidgets import QPushButton
    for b in widget.findChildren(QPushButton):
        if b.text().strip() == text_or_tip or b.toolTip() == text_or_tip:
            b.click()
            return True
    return False


def t20_add_employee_button():
    """Bouton « + Ajouter » de la barre d'en-tête → formulaire → Enregistrer."""
    from Blado.views.main_window import MainWindow
    from Blado.views.staff_form import StaffFormDialog
    mw = MainWindow()
    mw._switch_to("employees")

    def handler(dlg):
        dlg._f_first_name.setText("Beta")
        dlg._f_last_name.setText(f"{MARK}Beta")
        _click_button(dlg, "Activer")
    _DIALOG_HANDLERS[StaffFormDialog] = handler
    mw._on_add()
    _DIALOG_HANDLERS.pop(StaffFormDialog, None)
    rows = _query("SELECT id, is_active, emp_status FROM blado_employee WHERE last_name=%s",
                  (f"{MARK}Beta",))
    check("« + Ajouter » (en-tête) → employé créé", bool(rows) and rows[0][1] is True,
          str(rows))
    if rows:
        CREATED["employees"].append(rows[0][0])
    mw.close(); mw.deleteLater()


def t21_absences_add_button():
    """Bouton « + Ajouter » de la page Absences → dialogue avec sélecteur d'employé."""
    from Blado.views.main_window import MainWindow
    from Blado.views.staff_events import StaffEventDialog
    mw = MainWindow()
    mw._switch_to("absences")
    picked = {}

    def handler(dlg):
        if dlg._staff_combo is None or dlg._staff_combo.count() == 0:
            return
        picked["staff_id"] = dlg._staff_combo.itemData(0)
        dlg._staff_combo.setCurrentIndex(0)
        dlg._select_mode("Ab")
        dlg._motif_field.setCurrentIndex(0)
        dlg._note.setPlainText(f"{MARK} bouton absences")
        _click_button(dlg, "Enregistrer")
    _DIALOG_HANDLERS[StaffEventDialog] = handler
    mw._on_add()
    _DIALOG_HANDLERS.pop(StaffEventDialog, None)
    sid = picked.get("staff_id")
    check("« + Ajouter » (absences) → sélecteur d'employé présent", sid is not None)
    if sid:
        rows = _query(
            "SELECT COUNT(*) FROM blado_event WHERE staff_id=%s AND note=%s",
            (sid, f"{MARK} bouton absences"))
        check("Événement créé via le bouton de la page", rows[0][0] == 1, str(rows[0][0]))
    mw.close(); mw.deleteLater()


def t22_catalog_button():
    """Courriers : « + Nouveau modèle » → catalogue → Sélectionner ce modèle."""
    from Blado.views.main_window import MainWindow
    from Blado.views.letter_dialogs import _CatalogDialog
    # Modèle standard temporaire (is_builtin) pour peupler le catalogue
    # NB : consommer le résultat du RETURNING avant commit (sinon psycopg2
    # lève « no results to fetch » au prochain execute sur la connexion)
    _tmp_cur = _conn.cursor()
    _tmp_cur.execute("INSERT INTO blado_letter_template (family, code, title, description, is_builtin)"
                     " VALUES ('A','STDA01','Standard test','Standard pour test flux UI', TRUE)"
                     " RETURNING id")
    _tmp_cur.fetchone()
    _conn.commit()
    mw = MainWindow()
    mw._switch_to("letters")
    lm = mw._pages["letters"]

    def handler(dlg):
        dlg._switch("A")
        tpls = BladoDatabase.get_letter_templates(family="A", active_only=True)
        std = next((t for t in tpls if t.get("is_builtin") and t.get("code") == "STDA01"), None)
        if std is None:
            return
        dlg._on_card_click(std, None)
        dlg._on_confirm()
    _DIALOG_HANDLERS[_CatalogDialog] = handler
    lm._on_new_model()
    _DIALOG_HANDLERS.pop(_CatalogDialog, None)
    rows = _query("SELECT id, code, title FROM blado_letter_template WHERE code=%s",
                  ("AEC-STDA01",))
    check("Catalogue → modèle entreprise « AEC-STDA01 » créé", bool(rows), str(rows))
    mw.close(); mw.deleteLater()


def t23_generate_button():
    """Courriers : carte modèle → bouton « Générer » → Générer et sauvegarder."""
    from Blado.views.main_window import MainWindow
    from Blado.views.letter_dialogs import _GenerateLetterDialog
    mw = MainWindow()
    mw._switch_to("letters")
    lm = mw._pages["letters"]
    tpls = BladoDatabase.get_letter_templates(family="A", active_only=True)
    tpl = next((t for t in tpls if t.get("code") == "AEC-STDA01"), None)
    staff = BladoDatabase.search_staff(0, 0, False, f"{MARK}Alpha", {})
    check("Prérequis : modèle AEC-STDA01 + employé test", tpl is not None and bool(staff))
    if tpl and staff:
        lm.set_staff(staff[0])

        def handler(dlg):
            dlg._objet_field.setText(f"{MARK} bouton générer")
            _click_button(dlg, "Générer et sauvegarder")
        _DIALOG_HANDLERS[_GenerateLetterDialog] = handler
        lm._on_generate(tpl)
        _DIALOG_HANDLERS.pop(_GenerateLetterDialog, None)
        rows = _query(
            "SELECT COUNT(*) FROM blado_generated_letter WHERE template_id=%s",
            (tpl["id"],))
        check("Courrier créé via le bouton « Générer » de la carte", rows[0][0] > 0,
              str(rows[0][0]))
    mw.close(); mw.deleteLater()


def t24_settings_add_buttons():
    """Paramètres : « + Ajouter un consultant » et « + Ajouter une entreprise »."""
    from Blado.views.main_window import MainWindow
    from Blado.views.settings_page import ConsultantDialog, EntrepriseDialog
    mw = MainWindow()
    mw._switch_to("settings")
    sp = mw._pages["settings"]

    def hc(dlg):
        dlg._f_nom.setText(f"{MARK}CabinetBouton")
        _click_button(dlg, "Enregistrer")
    _DIALOG_HANDLERS[ConsultantDialog] = hc
    sp._on_add_consultant()
    _DIALOG_HANDLERS.pop(ConsultantDialog, None)
    check("Paramètres → consultant créé via bouton",
          bool(_query("SELECT id FROM consultants WHERE nom=%s", (f"{MARK}CabinetBouton",))))

    def he(dlg):
        dlg._f_nom.setText(f"{MARK}ClientBouton")
        _click_button(dlg, "Enregistrer")
    _DIALOG_HANDLERS[EntrepriseDialog] = he
    sp._on_add_entreprise()
    _DIALOG_HANDLERS.pop(EntrepriseDialog, None)
    check("Paramètres → entreprise créée via bouton",
          bool(_query("SELECT id FROM entreprises WHERE nom=%s", (f"{MARK}ClientBouton",))))
    mw.close(); mw.deleteLater()


def t25_service_activate_button():
    """Services : « + Activer un service » via le bouton réel."""
    from Blado.views.main_window import MainWindow
    from Blado.views.service_page import ServiceDialog
    mw = MainWindow()
    mw._switch_to("services")
    svp = mw._pages["services"]
    disabled = BladoDatabase.get_first_disabled_service()
    if not disabled:
        print("ℹ️  Aucun service désactivé — bouton « + Activer » non testé")
        mw.close(); mw.deleteLater()
        return
    _DIALOG_HANDLERS[ServiceDialog] = lambda dlg: None
    svp._on_add_service()
    _DIALOG_HANDLERS.pop(ServiceDialog, None)
    CREATED["services_activated"].append(disabled["id"])
    enabled = _query("SELECT enabled FROM services WHERE id=%s", (disabled["id"],))[0][0]
    gabarit = _query("SELECT COUNT(*) FROM blado_employee WHERE fk_service_id=%s",
                     (disabled["id"],))[0][0]
    check("« + Activer un service » → service activé + gabarit créé",
          enabled is True and gabarit > 0, f"enabled={enabled}, gabarit={gabarit}")
    mw.close(); mw.deleteLater()


def t26_grid_csv_button():
    """Grille employés : bouton « CSV » → export réel du fichier."""
    from Blado.views.main_window import MainWindow
    mw = MainWindow()
    mw._switch_to("employees")
    grid = mw._pages["employees"]
    _click_button(grid, "CSV")
    out = os.path.join(_TEST_OUT_DIR, "courrier_test.docx")  # chemin retourné par le patch
    check("Export CSV écrit un fichier", os.path.isfile(out), out)
    mw.close(); mw.deleteLater()


def t27_payslip_launch_button():
    """Paie : bouton « Lancer la paie » → bascule vers la page de lancement."""
    from Blado.views.main_window import MainWindow
    mw = MainWindow()
    mw._switch_to("payroll")
    pp = mw._pages["payroll"]
    clicked = _click_button(pp, "Lancer la paie")
    check("Bouton « Lancer la paie » cliqué", clicked)
    check("Navigation vers la page de lancement",
          mw._pages.get("payslip_run") is not None)
    mw.close(); mw.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
# Nettoyage — supprime toutes les données de test + artefacts
# ═══════════════════════════════════════════════════════════════════════════
def cleanup():
    print("\n── Nettoyage des données de test ──")
    cur = _conn.cursor()
    emp_ids = [r[0] for r in _query(
        "SELECT id FROM blado_employee WHERE last_name LIKE %s", (f"{MARK}%",))]
    tpl_ids = [r[0] for r in _query(
        "SELECT id FROM blado_letter_template WHERE title LIKE %s OR code = 'TSTF001'",
        (f"{MARK}%",))]

    if emp_ids:
        cur.execute("DELETE FROM blado_generated_letter WHERE staff_id = ANY(%s)", (emp_ids,))
        cur.execute("DELETE FROM blado_payslip_line WHERE payslip_id IN "
                    "(SELECT id FROM blado_payslip WHERE employee_id = ANY(%s))", (emp_ids,))
        cur.execute("DELETE FROM blado_payslip WHERE employee_id = ANY(%s)", (emp_ids,))
        cur.execute("DELETE FROM blado_dossier_check WHERE staff_id = ANY(%s)", (emp_ids,))
        cur.execute("DELETE FROM blado_degree WHERE staff_id = ANY(%s)", (emp_ids,))
        cur.execute("DELETE FROM blado_language WHERE staff_id = ANY(%s)", (emp_ids,))
        cur.execute("DELETE FROM blado_employee WHERE id = ANY(%s)", (emp_ids,))
        print(f"Employés de test supprimés : {len(emp_ids)}")
    if tpl_ids:
        cur.execute("DELETE FROM blado_generated_letter WHERE template_id = ANY(%s)", (tpl_ids,))
        cur.execute("DELETE FROM blado_letter_template WHERE id = ANY(%s)", (tpl_ids,))
        print(f"Modèles de courrier de test supprimés : {len(tpl_ids)}")
    # Modèles du flux « Catalogue » (standard STDA01 + copie entreprise AEC-STDA01)
    cur.execute("DELETE FROM blado_generated_letter WHERE template_id IN "
                "(SELECT id FROM blado_letter_template WHERE code LIKE '%STDA01')")
    cur.execute("DELETE FROM blado_letter_template WHERE code LIKE '%STDA01'")
    # Événements créés via les boutons (note marquée)
    cur.execute("DELETE FROM blado_event WHERE note LIKE %s", (f"{MARK}%",))
    # Courriers générés dans le dossier de test
    cur.execute("DELETE FROM blado_generated_letter WHERE file_path LIKE %s", ("%_testflow%",))
    cur.execute("DELETE FROM missions WHERE reference LIKE %s", (f"{MARK}%",))
    cur.execute("DELETE FROM consultants WHERE nom LIKE %s", (f"{MARK}%",))
    cur.execute("DELETE FROM entreprises WHERE nom LIKE %s", (f"{MARK}%",))
    # Bulletins du mois de test (générés pour TOUS les employés à contrat)
    month, year = QDate.currentDate().month(), QDate.currentDate().year()
    cur.execute("DELETE FROM blado_payslip_line WHERE payslip_id IN "
                "(SELECT id FROM blado_payslip WHERE period_month=%s AND period_year=%s)",
                (month, year))
    cur.execute("DELETE FROM blado_payslip WHERE period_month=%s AND period_year=%s",
                (month, year))
    print(f"Bulletins du mois {month}/{year} supprimés (artefacts de la paie test)")
    # Restaurer l'état des services modifiés
    for svc_id, old_ent in CREATED.get("service_ent_restore", {}).items():
        cur.execute("UPDATE services SET entreprise_id=%s WHERE id=%s", (old_ent, svc_id))
    for svc_id in CREATED.get("services_activated", []):
        cur.execute("UPDATE services SET enabled=FALSE WHERE id=%s", (svc_id,))
    # Dossiers uploads du test
    for emp_id in emp_ids:
        up = os.path.join(ROOT, "uploads", str(emp_id))
        if os.path.isdir(up):
            shutil.rmtree(up, ignore_errors=True)
    if os.path.isdir(_TEST_OUT_DIR):
        shutil.rmtree(_TEST_OUT_DIR, ignore_errors=True)
    _conn.commit()
    print("✅ Nettoyage terminé")


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        cleanup()
        sys.exit(0)

    print("=== Blado — Tests de flux UI complets ===\n")
    # L'ordre compte : chaque flux dépend du précédent.
    _emp = None
    def _t1():
        global _emp
        _emp = t1_create_employee()
    flow("1. Création employé (mode rapide)", _t1)
    if _emp:
        flow("2. Édition complète employé", lambda: t2_edit_employee(_emp))
        flow("3. Fiche employé — sections", lambda: t3_staff_detail(_emp))
        flow("4. Contrat", lambda: t4_contract(_emp))
        flow("5. Congé", lambda: t5_leave(_emp))
        flow("6. Événement absence", lambda: t6_event(_emp))
        flow("7. Document", lambda: t7_document(_emp))
        flow("11. Service + héritage client", lambda: t11_service(_emp))
        flow("12. Paie du mois", lambda: t12_payroll(_emp))
        flow("13. Courriers (modèle + génération)", lambda: t13_letters(_emp))
    else:
        print("⚠️  Flux 2-13 ignorés (employé de test non créé)")
    flow("8. Mission", t8_mission)
    flow("9. Consultant (cabinet)", t9_consultant)
    flow("10. Entreprise cliente", t10_entreprise)
    flow("14. Validation nom vide", t14_validation)
    flow("15. Changement de thèmes", t15_themes)

    # ── Partie 2 : clics réels sur les boutons des pages ──
    print("\n── Partie 2 : clics réels sur les boutons des pages ──")
    flow("20. « + Ajouter » en-tête (employé)", t20_add_employee_button)
    flow("21. « + Ajouter » absences (sélecteur employé)", t21_absences_add_button)
    flow("22. Courriers — « + Nouveau modèle » (catalogue)", t22_catalog_button)
    flow("23. Courriers — bouton « Générer » de la carte", t23_generate_button)
    flow("24. Paramètres — boutons « + Ajouter »", t24_settings_add_buttons)
    flow("25. Services — bouton « + Activer un service »", t25_service_activate_button)
    flow("26. Grille — bouton « CSV »", t26_grid_csv_button)
    flow("27. Paie — bouton « Lancer la paie »", t27_payslip_launch_button)

    print(f"\n{'='*50}")
    print(f"Vérifications : {CHECKS} | Échecs : {FAILURES}")
    if FAILURES == 0:
        print("✅ Tous les flux UI passent")
    else:
        print("❌ Des flux échouent — corrections nécessaires")
    print(f"(nettoyage : python test_ui_flows.py --cleanup)")
    sys.exit(1 if FAILURES else 0)
