"""Fixtures pytest-qt pour Blado — environnement offscreen + intranet bladodb réelle.

Importé automatiquement par pytest. L'environnement offscreen DOIT être posé
avant la création de la QApplication (d'où le setdefault en tête de module).
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "BladoCommon"))

import pytest  # noqa: E402

from bladocommon.database import db  # noqa: E402
from bladocommon.theme import theme_manager  # noqa: E402
from bladocommon.session import session  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """QApplication unique pour la session (override du qapp pytest-qt).

    Relie le theme_manager et la base intranet — les constructions de
    dialogues lisent la base réelle (mêmes conditions que test_ui_flows).
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    theme_manager.bind(app)
    assert db.connect_intranet(), "Connexion intranet bladodb impossible"
    session.mode = "consultant"
    yield app


@pytest.fixture
def staff_data():
    """Employé factice (non présent en base) pour les dialogues."""
    return {
        "id": 999999,
        "first_name": "Test",
        "last_name": "Widget",
        "full_name": "Test Widget",
        "email": "",
        "emp_status": "actif",
        "fk_service_id": None,
        "service_label": "",
        "service_color": "#cccccc",
    }


@pytest.fixture
def real_staff():
    """Premier employé réel de la base (lecture seule)."""
    from Blado.common.blado_database import BladoDatabase

    rows = BladoDatabase.search_staff(1, 500, False, "", {})
    assert rows, "aucun employé réel en base"
    return rows[0]
