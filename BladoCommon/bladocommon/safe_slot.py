"""
safe_slot — Decorateur pour proteger les slots Qt contre les crashes silencieux.

Usage:
    from bladocommon.safe_slot import safe_slot, set_debug

    @safe_slot("LoginWindow.btn_connect")
    def _on_connect(self):
        ...

    set_debug(True)   # Dev
    set_debug(False)  # Prod
"""

import functools
import time
import traceback

from PySide6.QtWidgets import QMessageBox

from bladocommon.logger import log as logger

DEBUG = False


def set_debug(enabled: bool):
    """Active/desactive les logs de debug pour tous les safe_slot."""
    global DEBUG
    DEBUG = enabled


def safe_slot(label: str = ""):
    """Decore un slot Qt : loggue START/OK/ERROR et empeche les crashes silencieux.

    Args:
        label: Identifiant unique du slot, ex: "MainWindow.btn_save_student".

    En mode DEBUG :
        - Loggue START avec timestamp
        - Loggue OK avec duree d'execution
        - En cas d'erreur : log + QMessageBox.critical

    En mode PROD (DEBUG=False) :
        - Loggue ERROR uniquement
        - Pas de boite de dialogue (silencieux)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            if DEBUG:
                logger(f"[SLOT] {label} | START")
            try:
                result = func(*args, **kwargs)
                if DEBUG:
                    elapsed = (time.time() - t0) * 1000
                    logger(f"[SLOT] {label} | OK ({elapsed:.0f}ms)")
                return result
            except Exception as e:
                tb = traceback.format_exc()
                logger(f"[SLOT] {label} | ERROR: {e}\n{tb}")
                if DEBUG:
                    parent = None
                    for arg in args:
                        if hasattr(arg, 'parent'):
                            try:
                                parent = arg.parent()
                            except Exception:
                                pass
                            break
                    QMessageBox.critical(
                        parent, "Erreur",
                        f"[{label}]\n\n{type(e).__name__}: {e}"
                    )
        return wrapper
    return decorator
