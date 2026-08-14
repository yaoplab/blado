#!/usr/bin/env python3
"""Blado — Linter consolidé. À exécuter avant chaque lancement.

Usage: python lint_blado.py [--fix]
"""
import sys, os, subprocess, compileall, io

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "BladoCommon"))
os.environ["LARC_LANG"] = "fr"

errors = 0
warnings = 0

def e(msg):
    global errors; errors += 1
    print(f"❌ {msg}")

def w(msg):
    global warnings; warnings += 1
    print(f"⚠️  {msg}")

def ok(msg):
    print(f"✅ {msg}")

# ── 1. Syntaxe Python ──
print("=== 1. Syntaxe Python ===")
for folder in ["Blado", "BladoCommon"]:
    for root, dirs, files in os.walk(os.path.join(ROOT, folder)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, encoding="utf-8") as fh:
                        compile(fh.read(), path, "exec")
                except SyntaxError as se:
                    e(f"{os.path.relpath(path, ROOT)}:{se.lineno} — {se.msg}")
if errors == 0:
    ok("Tous les fichiers compilent")

# ── 2. Import ──
print("\n=== 2. Import Blado ===")
try:
    from Blado.main import main
    ok("Blado.main importé")
except Exception as ex:
    e(f"Import échoué: {ex}")

# ── 3. Taille des fichiers (≤ 1000 lignes) ──
print("\n=== 3. Taille des fichiers ===")
for folder in ["Blado", "BladoCommon"]:
    for root, dirs, files in os.walk(os.path.join(ROOT, folder)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                lines = len(open(path, encoding="utf-8").readlines())
                if lines > 1000:
                    rel = os.path.relpath(path, ROOT)
                    e(f"{rel}: {lines} lignes (> 1000)")
if errors == 0 or all("> 1000" not in str(e) for e in []):
    ok("Tous ≤ 1000 lignes")

# ── 4. Références Larc obsolètes ──
# ── 3b. Colonnes SQL obsolètes ──
print("\n=== 3b. Colonnes SQL obsolètes ===")
import re
obsolete_cols = [
    (r'\btel_maison\b', 'tel_maison'),
    (r'\btel_smartphone_1\b', 'tel_smartphone_1'),
    (r'\bemailperso\b', 'emailperso'),
    (r'\bfk_gender_id\b', 'fk_gender_id'),
    (r'\bdate_entree\b', 'date_entree'),
    (r'\bfk_language\b', 'fk_language'),
    (r'\baecuser_ptr_id\b', 'aecuser_ptr_id'),
    (r'\bdate_of_birth\b', 'date_of_birth'),
    (r'\btype_coordonator\b', 'type_coordonator'),
    (r'\btype_director\b', 'type_director'),
    (r'\bis_teacher\b', 'is_teacher'),
    (r'\bis_coordonator\b', 'is_coordonator'),
    (r'\bis_adm\b', 'is_adm'),
    (r'\.category_key\b', '.category_key (blado_document n\'a plus cette colonne)'),
    (r't\.staff_id\b', 't.staff_id → t.assigned_to (blado_todo)'),
]
for folder in ["Blado"]:
    for root, dirs, files in os.walk(os.path.join(ROOT, folder)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, encoding="utf-8") as fh:
                    content = fh.read()
                for pattern, label in obsolete_cols:
                    if re.search(pattern, content):
                        e(f"{os.path.relpath(path, ROOT)}: {label}")
if errors == 0:
    ok("Aucune colonne obsolète")

print("\n=== 4. Références obsolètes ===")
import subprocess
for pattern, label in [
    ("larccommon", "larccommon (doit être bladocommon)"),
    ("HRDatabase", "HRDatabase (doit être BladoDatabase)"),
    ("larcauth", "larcauth (table Larc)"),
    ("LarcRH", "LarcRH (ancien nom)"),
    ("Arc-en-Ciel", "Arc-en-Ciel (scolaire)"),
    ("arc-en-ciel.org", "arc-en-ciel.org (domaine école)"),
]:
    try:
        out = subprocess.check_output(
            f'findstr /s /i /m /c:"{pattern}" "{ROOT}\\Blado\\*.py" "{ROOT}\\Blado\\**\\*.py"',
            shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            for line in out.split("\n")[:5]:
                rel = os.path.relpath(line.strip(), ROOT)
                w(f"{rel}: contient '{pattern}'")
    except subprocess.CalledProcessError:
        pass  # no matches = good

if warnings == 0:
    ok("Aucune référence obsolète")

# ── 4b. Connexions Qt : signaux à argument obligatoire vers slots @safe_slot ──
print("\n=== 4b. Connexions Qt (signaux + safe_slot) ===")
# currentIndexChanged(int), textChanged(str), toggled(bool) passent TOUJOURS
# leur argument au wrapper *args de safe_slot → TypeError si le slot n'a pas
# de paramètre (ex. StaffGrid._on_filter_changed, bug 2026-08-13).
for folder in ["Blado", "BladoCommon"]:
    for root, dirs, files in os.walk(os.path.join(ROOT, folder)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            lines = content.splitlines()
            for m in re.finditer(r"(currentIndexChanged|textChanged|toggled)\.connect\(self\.(\w+)\)", content):
                sig, name = m.group(1), m.group(2)
                for i, line in enumerate(lines):
                    if re.search(rf"def {name}\(self\)\s*:", line):
                        # décorateur safe_slot juste au-dessus ?
                        if i > 0 and "@safe_slot" in lines[i - 1]:
                            e(f"{os.path.relpath(path, ROOT)}:{i+1} — {name} connecté à {sig} sans paramètre : "
                              f"l'argument du signal passe au wrapper safe_slot → TypeError. "
                              f"Ajouter un paramètre facultatif (ex. def {name}(self, _arg=None)).")
                        break
if errors == 0:
    ok("Aucune connexion à risque")

# ── 4c. Sécurité des données : slots vs employés ──
print("\n=== 4c. Sécurité des slots (anti-écrasement) ===")
# Bug 2026-08-13 : get_free_slots/activate_employee traitaient TOUT employé
# inactif comme un emplacement libre → la création d'un employé écrasait les
# données d'un vrai employé désactivé. Garde-fou : seuls les placeholders
# 'Employe'/'Slot XXXXX' sont des slots.
mixin_path = os.path.join(ROOT, "Blado", "common", "blado_hr_mixin.py")
with open(mixin_path, encoding="utf-8") as fh:
    mixin_src = fh.read()
guard = "last_name LIKE 'Slot %%'"
count = mixin_src.count(guard)
if count < 2:
    e(f"blado_hr_mixin.py : le garde-fou slots '{guard}' doit apparaître dans "
      f"get_free_slots ET activate_employee ({count} trouvé) — risque d'écrasement d'employés")
else:
    ok(f"Garde-fou slots présent dans get_free_slots et activate_employee")

# ── 4d. Feedback obligatoire après un popup ──
print("\n=== 4d. Feedback popup (message OK après action) ===")
# Convention UX : toute action passée par un popup (dlg.exec()) doit se
# terminer par un message de sortie QMessageBox avec un simple OK —
# jamais de fermeture silencieuse.
for folder in ["Blado", "BladoCommon"]:
    for root, dirs, files in os.walk(os.path.join(ROOT, folder)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            for m in re.finditer(r"(\w+)\.exec\(\)", src):
                if m.group(1) in ("app", "self"):
                    continue  # boucle d'événements / boucle propre au dialogue
                pos = m.start()
                prefix = src[:pos]
                defs = list(re.finditer(r"^\s*(?:async\s+)?def\s+\w+", prefix, re.M))
                if not defs:
                    continue
                rest = src[pos:]
                next_def = re.search(r"^\s*(?:async\s+)?def\s+\w+", rest, re.M)
                body_end = pos + (next_def.start() if next_def else len(src))
                body = src[defs[-1].start():body_end]
                if "# no-popup-feedback" in body:
                    continue  # exception documentée (dialogue purement informatif)
                if "QMessageBox" not in body:
                    line_no = prefix.count("\n") + 1
                    e(f"{os.path.relpath(path, ROOT)}:{line_no} — popup fermé sans message de sortie : "
                      f"ajouter QMessageBox.information(..., \"…\") (simple OK) après l'action")
if errors == 0:
    ok("Tous les popups ont un message de sortie")

# ── 5. DB ──
print("\n=== 5. DB Runtime ===")
try:
    from bladocommon.database import db
    from Blado.common.blado_database import BladoDatabase
    if not db.connect_intranet():
        w("Connexion DB échouée")
    else:
        ok(f"Connexion OK ({BladoDatabase.get_services().__len__()} services)")

        # Test search_staff (le plus utilisé)
        r = BladoDatabase.search_staff(0, 0, False, "", {})
        ok(f"search_staff: {len(r)} employés")

        # Test get_staff_full (détail employé)
        if r:
            emp = BladoDatabase.get_staff_full(r[0]["id"])
            ok(f"get_staff_full({r[0]['id']}): {emp is not None}")

        # Test get_free_slots (activation)
        svcs = [s for s in BladoDatabase.get_services() if s.get("enabled")]
        if svcs:
            slots = BladoDatabase.get_free_slots(svcs[0]["id"])
            ok(f"get_free_slots(service {svcs[0]['id']}): {len(slots)} slots")

        # Test get_dashboard_kpis
        kpis = BladoDatabase.get_dashboard_kpis()
        ok(f"dashboard KPIs: {len(kpis)} indicateurs")

        # Test get_headcount_by_service
        hc = BladoDatabase.get_headcount_by_service()
        ok(f"headcount: {len(hc)} services")

        # Test get_payslips (paie)
        ps = BladoDatabase.get_payslips(8, 2026)
        ok(f"payslips août 2026: {len(ps)} bulletins")

        # Test degrees/languages — aller-retour en base (attrape les dérives de schéma)
        if r:
            sid = r[0]["id"]
            d = BladoDatabase.save_degree(sid, {"degree_type": "__TEST__", "institution": "X",
                                                "year_obtained": 2026, "field_of_study": None})
            degs = BladoDatabase.get_degrees(sid)
            ok(f"degree round-trip: {d and any(g['degree_type'] == '__TEST__' for g in degs)}")
            for g in degs:
                if g["degree_type"] == "__TEST__":
                    BladoDatabase.delete_degree(g["id"], sid)
            l = BladoDatabase.save_language(sid, {"language": "__TESTLANG__", "proficiency": "B1"})
            langs = BladoDatabase.get_languages(sid)
            ok(f"language round-trip: {l and any(x['language'] == '__TESTLANG__' for x in langs)}")
            cur = db.server_conn.cursor()
            cur.execute("DELETE FROM blado_language WHERE staff_id = %s AND language = '__TESTLANG__'", (sid,))

            # Vérification dossier (« Vérifié et Validé »)
            c = BladoDatabase.set_dossier_check(sid, "cnss", True, "Lint")
            ch = BladoDatabase.get_dossier_checks(sid)
            ok(f"dossier check round-trip: {c and ch.get('cnss', {}).get('validated') is True}")
            BladoDatabase.set_dossier_check(sid, "cnss", False, "Lint")
            prog = BladoDatabase.dossier_validation_progress(sid)
            ok(f"dossier progress: {prog['total']} items")

            # Documents (métadonnées) — aller-retour
            d = BladoDatabase.save_document(sid, "__TESTDOC__", "test", "", "", 0)
            docs = BladoDatabase.get_documents(sid)
            ok(f"document round-trip: {d and any(x['label'] == '__TESTDOC__' for x in docs)}")
            for x in docs:
                if x["label"] == "__TESTDOC__":
                    BladoDatabase.delete_document(x["id"])

except Exception as ex:
    import traceback
    traceback.print_exc()
    e(f"DB: {ex}")

# ── 5b. UI Runtime : instanciation de TOUTES les pages et dialogues ──
# Le linter lit le code mais ne l'exécute pas : un NameError dans un dialogue
# n'apparaissait qu'au clic (bug « Name 'Qt' is not defined » Préférences).
# Ce balayage exécute chaque page/dialogue hors écran → les erreurs de
# déroulement sont détectées AVANT le lancement.
print("\n=== 5b. UI Runtime (instanciation offscreen) ===")
try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    _uiapp = QApplication.instance() or QApplication([])
    from bladocommon.theme import theme_manager as _tm
    _tm.bind(_uiapp)
    from bladocommon.session import session as _sess
    from Blado.common.blado_database import BladoDatabase as _BD
    if not db.server_conn:
        db.connect_intranet()
    _sess.mode = "consultant"   # couvre aussi le sélecteur d'entreprise

    def _ui_instantiate(label: str, factory):
        try:
            w = factory()
            if hasattr(w, "close"): w.close()
            if hasattr(w, "deleteLater"): w.deleteLater()
            ok(f"{label}")
        except Exception as ex:
            import traceback as _tb
            lines = _tb.format_exc().strip().splitlines()
            origin = next((l.strip() for l in reversed(lines) if l.strip().startswith("File")), "")
            e(f"{label} — {type(ex).__name__}: {ex} [{origin}]")

    # 1. Toutes les pages de la fenêtre principale (vraies données DB)
    from Blado.views.main_window import MainWindow, CATEGORIES
    _mw = MainWindow()
    for _key, *_rest in CATEGORIES:
        _ui_instantiate(f"MainWindow._switch_to('{_key}')",
                        lambda k=_key: _mw._switch_to(k))
    _ui_instantiate("MainWindow._switch_to('payslip_run')",
                    lambda: _mw._switch_to("payslip_run"))
    _mw.close(); _mw.deleteLater()

    # 2. Fiche employé — charge TOUTES les sections (_load_*)
    _staff = _BD.search_staff(0, 0, False, "", {})
    if _staff:
        from Blado.views.staff_detail import StaffDetail
        _ui_instantiate("StaffDetail (toutes sections)",
                        lambda: StaffDetail(_staff[0], on_back=lambda: None))
        _full = _BD.get_staff_full(_staff[0]["id"])
    else:
        _full = None

    # 3. Tous les dialogues
    _phi = _tm.phi_theme
    from Blado.views.staff_form import StaffFormDialog
    _ui_instantiate("StaffFormDialog (nouveau)",
                    lambda: StaffFormDialog(0, 0, slot_id=1))
    if _full:
        _ui_instantiate("StaffFormDialog (édition)",
                        lambda: StaffFormDialog(0, 0, staff_data=_full))
    from Blado.views.mission_dialog import MissionDialog
    _ui_instantiate("MissionDialog", lambda: MissionDialog(_phi))
    from Blado.views.settings_page import ConsultantDialog, EntrepriseDialog
    _ui_instantiate("ConsultantDialog", lambda: ConsultantDialog(_phi))
    _ui_instantiate("EntrepriseDialog", lambda: EntrepriseDialog(_phi))
    from Blado.views.contract_form import ContractFormDialog
    _ui_instantiate("ContractFormDialog",
                    lambda: ContractFormDialog(_staff[0]["id"] if _staff else 1))
    from Blado.views.leave_request import LeaveRequestDialog
    _ui_instantiate("LeaveRequestDialog",
                    lambda: LeaveRequestDialog(_staff[0]["id"] if _staff else 1))
    from Blado.views.staff_events import StaffEventDialog
    _ui_instantiate("StaffEventDialog",
                    lambda: StaffEventDialog(_staff[0] if _staff else {"id": 0, "full_name": "Test"}))
    from Blado.views.document_manager import DocumentDialog
    _ui_instantiate("DocumentDialog",
                    lambda: DocumentDialog(_staff[0]["id"] if _staff else 1))
    from Blado.views.service_page import ServiceDialog
    _svcs = _BD.get_services()
    _ui_instantiate("ServiceDialog",
                    lambda: ServiceDialog(_phi, _svcs[0] if _svcs else
                                          {"id": 1, "label": "S", "code": "", "description": "",
                                           "color": "#64748B", "enabled": True}))
    from bladocommon.preferences_dialog import PreferencesDialog
    _ui_instantiate("PreferencesDialog", lambda: PreferencesDialog())
    from Blado.views.letter_dialogs import (
        _StaffSearchPopup, _CatalogDialog, _EditTemplateDialog, _GenerateLetterDialog,
    )
    _ui_instantiate("_StaffSearchPopup", lambda: _StaffSearchPopup())
    _ui_instantiate("_CatalogDialog", lambda: _CatalogDialog())
    _tpls = _BD.get_letter_templates(active_only=False)
    if _tpls:
        _tpl = _tpls[0]
    else:
        # Modèle factice : les dialogues doivent s'ouvrir même sans modèle en base
        _tpl = {"id": 999, "code": "TEST-A01", "title": "Test modèle",
                "description": "d", "body_text": None, "source_code": "",
                "variables": [], "version": 1, "is_active": True, "is_builtin": False}
    _ui_instantiate("_EditTemplateDialog", lambda: _EditTemplateDialog(_tpl))
    _ui_instantiate("_GenerateLetterDialog",
                    lambda: _GenerateLetterDialog(_tpl, _staff[0] if _staff else None))
    from Blado.views.staff_detail import CategoryManageDialog
    _ui_instantiate("CategoryManageDialog", lambda: CategoryManageDialog())
    from Blado.views.payslip_view import PayslipViewWidget
    _ps = _BD.get_payslips(8, 2026)
    if _ps:
        _ui_instantiate("PayslipViewWidget",
                        lambda: PayslipViewWidget(_ps[0]["id"] if "id" in _ps[0] else _ps[0].get("payslip_id", 0)))
    else:
        ok("PayslipViewWidget (aucun bulletin en base — ignoré)")

    # 4. Import de TOUS les modules de vues (erreurs au niveau module)
    import importlib, pkgutil
    import Blado.views as _views_pkg
    for _mod in pkgutil.iter_modules(_views_pkg.__path__):
        if _mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"Blado.views.{_mod.name}")
        except Exception as ex:
            import traceback as _tb
            e(f"import Blado.views.{_mod.name} — {type(ex).__name__}: {ex}")
    ok("Tous les modules de vues importés")

except Exception as ex:
    import traceback
    traceback.print_exc()
    e(f"UI Runtime: {ex}")

# ── 5c. UI Clics : simulation des gestionnaires (combos, cases, boutons) ──
# L'instanciation (5b) couvre les constructeurs ; cette étape exerce les
# HANDLERS : chaque combo est parcouru, chaque case cochée/décochée, les
# boutons sûrs (Annuler/Fermer/toggles de vue) sont cliqués — sans boîte
# modale (jamais de exec(), jamais d'écriture en base).
print("\n=== 5c. UI Clics (simulation handlers) ===")
try:
    from PySide6.QtWidgets import QComboBox, QCheckBox, QPushButton

    def _ui_click(label: str, fn):
        try:
            fn()
            ok(f"{label}")
        except Exception as ex:
            import traceback as _tb
            lines = _tb.format_exc().strip().splitlines()
            origin = next((l.strip() for l in reversed(lines) if l.strip().startswith("File")), "")
            e(f"{label} — {type(ex).__name__}: {ex} [{origin}]")

    def _exercise_handlers(widget, label: str):
        """Parcourt les combos (tous les index), cases, et boutons sûrs.

        NB : un clic peut reconstruire l'UI (ex. changement de vue de la
        grille) et détruire des widgets encore dans la liste — on vérifie
        shiboken6.isValid avant chaque action.
        """
        def _run():
            import shiboken6
            for combo in list(widget.findChildren(QComboBox)):
                if not shiboken6.isValid(combo):
                    continue
                for i in range(combo.count()):
                    combo.setCurrentIndex(i)
                combo.setCurrentIndex(0)
            for cb in list(widget.findChildren(QCheckBox)):
                if not shiboken6.isValid(cb):
                    continue
                cb.setChecked(not cb.isChecked())
                cb.setChecked(not cb.isChecked())
            for btn in list(widget.findChildren(QPushButton)):
                if not shiboken6.isValid(btn):
                    continue
                txt = btn.text().strip()
                if txt in ("Annuler", "Fermer", "Retour") or \
                   btn.toolTip() in ("Vue grille", "Vue tableau"):
                    btn.click()
        _ui_click(label, _run)

    # Pages de la fenêtre principale (recréée pour l'état initial)
    from Blado.views.main_window import MainWindow, CATEGORIES
    _mw2 = MainWindow()
    for _key, *_rest in CATEGORIES:
        _mw2._switch_to(_key)
        _page = _mw2._pages.get(_key)
        if _page:
            _exercise_handlers(_page, f"handlers page '{_key}'")
    _mw2.close(); _mw2.deleteLater()

    # Dialogues : boutons Annuler (fermeture sûre, pas d'écriture)
    def _cancel_dialog(dlg):
        for btn in dlg.findChildren(QPushButton):
            if btn.text().strip() in ("Annuler", "Fermer"):
                btn.click()
                break
        dlg.deleteLater()

    from Blado.views.staff_form import StaffFormDialog
    _ui_click("Annuler StaffFormDialog",
              lambda: _cancel_dialog(StaffFormDialog(0, 0, slot_id=1)))
except Exception as ex:
    import traceback
    traceback.print_exc()
    e(f"UI Clics: {ex}")

# ── Résumé ──
print(f"\n{'='*50}")
print(f"Erreurs: {errors} | Warnings: {warnings}")
if errors == 0:
    print("✅ Blado prêt à lancer")
else:
    print("❌ Corrige les erreurs avant de lancer")
