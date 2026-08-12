"""Blado — Gestion des Ressources Humaines."""
import os
import sys

# BLADO: standalone — ajouter la racine et BladoCommon au path
# main.py est dans D:\Blado\Blado\ — le parent est la racine du projet
_package_dir = os.path.dirname(os.path.abspath(__file__))   # D:\Blado\Blado
_root = os.path.dirname(_package_dir)                        # D:\Blado
if _root not in sys.path:
    sys.path.insert(0, _root)

_blado_common = os.path.join(_root, "BladoCommon")
if os.path.isdir(_blado_common) and _blado_common not in sys.path:
    sys.path.insert(0, _blado_common)

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from bladocommon.l10n import _
from bladocommon.safe_slot import set_debug


def main() -> None:
    set_debug(True)
    app = QApplication(sys.argv)
    app.setApplicationName("Blado")
    app.setOrganizationName("Blado")
    app.setFont(QFont("Segoe UI", 10))

    # Appliquer le thème global
    from bladocommon.theme import theme_manager
    theme_manager.bind(app)

    from bladocommon.l10n import Translator
    lang = os.environ.get("LARC_LANG", "fr")
    Translator.instance(lang).load_dir(Translator.l10n_dir())

    from bladocommon.database import db
    from bladocommon.session import session, ConnMode, UserRole

    # Connexion intranet (cloud en fallback)
    db.connect_intranet()
    if not db.server_conn:
        db.connect_cloud()

    def _check_blado_access(email):
        """Vérifie que l'utilisateur a un compte blado_user actif."""
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            SELECT id, full_name, role
            FROM blado_user
            WHERE LOWER(email) = %s AND is_active = TRUE
            LIMIT 1
        """, (email.lower().strip(),))
        return cur.fetchone()

    def detecter_mode():
        """Détecte le mode: 'consultant' si consultant actif avec mission, sinon 'rh'."""
        conn = db.server_conn
        if not conn:
            return "rh"
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM consultants c
                JOIN missions m ON m.consultant_id = c.id
                WHERE c.est_actif = TRUE AND m.statut = 'active'
            """)
            count = cur.fetchone()[0]
            return "consultant" if count > 0 else "rh"
        except Exception:
            return "rh"

    def on_intranet_login(email, password):
        from bladocommon.auth import AuthManager
        result = AuthManager.auth_intranet(email, password)
        ok, res, err = result
        if not ok:
            return (False, None, err)
        row = _check_blado_access(res.email)
        if not row:
            return (False, None, "Accès réservé aux utilisateurs Blado autorisés.")
        session.user_id = res.user_id
        session.email = res.email
        session.full_name = res.full_name
        session.role = res.role
        session.conn_mode = ConnMode.INTRANET
        session.is_authenticated = True
        session.mode = detecter_mode()
        return (True, res, "")

    def on_cloud_login():
        from bladocommon.auth import OAuth2Manager
        result = OAuth2Manager.authenticate()
        ok, res, err = result
        if not ok:
            return (False, None, err)
        row = _check_blado_access(res.email)
        if not row:
            return (False, None, "Accès réservé aux utilisateurs Blado autorisés.")
        session.user_id = res.user_id
        session.email = res.email
        session.full_name = res.full_name
        session.role = res.role
        session.conn_mode = ConnMode.CLOUD
        session.is_authenticated = True
        session.mode = detecter_mode()
        return (True, res, "")

    def on_success():
        from Blado.views.main_window import MainWindow
        window = MainWindow()
        window.showMaximized()

    from bladocommon.login import LoginWindow
    login = LoginWindow(
        on_success=on_success,
        title_prefix="Blado",
        subtitle="Gestion des Ressources Humaines",
        on_intranet_login=on_intranet_login,
        on_cloud_login=on_cloud_login,
    )
    login.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
