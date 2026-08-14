"""Bascule des thèmes — qtbot : chaque thème s'applique et change la palette."""

from bladocommon.theme import theme_manager


def test_all_themes_apply(qtbot):
    names = theme_manager.names()
    assert len(names) >= 3
    original = theme_manager.active_name
    palettes = {}
    try:
        for key, label in names:
            assert theme_manager.set_active(key), f"set_active({key}) a échoué"
            palettes[key] = theme_manager.palette
        # Chaque thème a une palette propre (les palettes ne sont pas identiques)
        distinct = {id(p) for p in palettes.values()}
        assert len(distinct) == len(names), "les palettes devraient différer par thème"
        # Cohérence : le thème actif correspond au dernier appliqué
        assert theme_manager.active_name == names[-1][0]
    finally:
        theme_manager.set_active(original)


def test_theme_cycle_restores(qtbot):
    names = theme_manager.names()
    original = theme_manager.active_name
    try:
        for key, _ in names:
            theme_manager.set_active(key)
        theme_manager.set_active(original)
        assert theme_manager.active_name == original
    finally:
        theme_manager.set_active(original)
