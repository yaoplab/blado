"""Construction de chaque dialogue principal — qtbot (offscreen, base réelle en lecture)."""

from bladocommon.theme import theme_manager

from Blado.views.contract_form import ContractFormDialog
from Blado.views.leave_request import LeaveRequestDialog
from Blado.views.mission_dialog import MissionDialog


def test_mission_dialog_constructs(qtbot):
    dlg = MissionDialog(theme_manager.phi_theme)
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg.isVisible()


def test_contract_form_constructs(qtbot, real_staff):
    dlg = ContractFormDialog(real_staff["id"])
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg.isVisible()


def test_leave_request_constructs(qtbot, real_staff):
    dlg = LeaveRequestDialog(real_staff["id"])
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg.isVisible()
