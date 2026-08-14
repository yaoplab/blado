"""StaffFormDialog — qtbot : mode rapide (slot) vs mode complet (édition)."""

from Blado.common.blado_database import BladoDatabase
from Blado.views.staff_form import StaffFormDialog


def _first_free_slot():
    for svc in BladoDatabase.get_services():
        if svc.get("enabled"):
            slots = BladoDatabase.get_free_slots(svc["id"])
            if slots:
                return svc, slots[0]
    return None, None


def test_quick_mode_constructs(qtbot):
    svc, slot = _first_free_slot()
    assert slot, "aucun slot libre — seed incomplète ?"
    dlg = StaffFormDialog(0, 0, slot_id=slot["id"])
    qtbot.addWidget(dlg)
    dlg.show()
    # Mode rapide : uniquement nom + prénom + service
    assert hasattr(dlg, "_f_first_name") and hasattr(dlg, "_f_last_name")
    assert dlg._f_first_name.isVisible()
    assert not hasattr(dlg, "_f_first")  # le formulaire complet n'est pas construit


def test_full_mode_constructs(qtbot, real_staff):
    dlg = StaffFormDialog(0, 0, staff_data=real_staff)
    qtbot.addWidget(dlg)
    dlg.show()
    # Mode complet : formulaire détaillé
    assert hasattr(dlg, "_f_first") and hasattr(dlg, "_f_last")
    assert hasattr(dlg, "_f_email") and hasattr(dlg, "_f_matricule")
    assert not hasattr(dlg, "_f_first_name")
    # Les données de l'employé sont chargées
    assert dlg._f_first.text() == real_staff["first_name"]
    assert dlg._f_last.text() == real_staff["last_name"]
