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
            e = BladoDatabase.get_staff_full(r[0]["id"])
            ok(f"get_staff_full({r[0]['id']}): {e is not None}")

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

except Exception as ex:
    import traceback
    traceback.print_exc()
    e(f"DB: {ex}")

# ── Résumé ──
print(f"\n{'='*50}")
print(f"Erreurs: {errors} | Warnings: {warnings}")
if errors == 0:
    print("✅ Blado prêt à lancer")
else:
    print("❌ Corrige les erreurs avant de lancer")
