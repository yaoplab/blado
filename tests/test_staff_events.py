"""StaffEventDialog — qtbot : construction, modes, gardes, sauvegarde.

La sauvegarde est testée contre une connexion factice (aucune écriture en base).
"""

from PySide6.QtWidgets import QMessageBox

from Blado.views.staff_events import StaffEventDialog


def test_constructs(qtbot, staff_data):
    dlg = StaffEventDialog(staff_data)
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg._staff["id"] == staff_data["id"]
    assert not dlg._motif_field.isVisible()  # motif masqué tant qu'aucun mode
    assert dlg._selected_type in (None, "")


def test_select_mode_absence_shows_motifs(qtbot, staff_data):
    dlg = StaffEventDialog(staff_data)
    qtbot.addWidget(dlg)
    dlg.show()
    dlg._select_mode("Ab")
    assert dlg._selected_type == "Ab"
    assert dlg._motif_field.isVisible()
    assert dlg._motif_field.count() > 0


def test_select_mode_retard(qtbot, staff_data):
    dlg = StaffEventDialog(staff_data)
    qtbot.addWidget(dlg)
    dlg.show()
    dlg._select_mode("Rt")
    assert dlg._selected_type == "Rt"
    assert dlg._motif_field.isVisible()


def test_save_without_type_warns_and_stays_open(qtbot, staff_data, monkeypatch):
    dlg = StaffEventDialog(staff_data)
    qtbot.addWidget(dlg)
    dlg.show()
    warned = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: warned.append(a)),
    )
    dlg._selected_type = None
    dlg._on_save()
    assert warned, "un avertissement « sélectionner le type » est attendu"
    assert not dlg.result()  # pas d'accept()


def test_save_inserts_event(qtbot, staff_data, monkeypatch):
    from bladocommon.database import db
    from bladocommon.session import session

    class FakeCursor:
        def __init__(self):
            self.queries = []

        def execute(self, sql, params=()):
            self.queries.append((sql, params))

        def fetchone(self):
            return None  # session.user_id absent de blado_employee → created_by NULL

    class FakeConn:
        def cursor(self):
            return self._cur

    fake = FakeConn()
    fake._cur = FakeCursor()
    # server_conn est une propriété → on patch la connexion intranet sous-jacente
    monkeypatch.setattr(db, "_intranet", fake)
    monkeypatch.setattr(session, "user_id", 4242, raising=False)

    dlg = StaffEventDialog(staff_data)
    qtbot.addWidget(dlg)
    dlg.show()
    dlg._select_mode("Ab")
    dlg._motif_field.setCurrentIndex(0)
    dlg._note.setPlainText("Note widget test")
    dlg._on_save()

    # Le SQL multiligne commence par "\n    " → in, pas startswith
    inserts = [q for q in fake._cur.queries if "INSERT INTO blado_event" in q[0]]
    assert len(inserts) == 1
    sql, params = inserts[0]
    assert params[0] == staff_data["id"]
    assert params[1] == f"Absence — {dlg._motif_field.currentText()}"
    assert params[4] == "RH"  # source
    assert params[5] is None  # created_by NULL (id non employé)
