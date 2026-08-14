"""MainWindow Blado — sidebar 4 catégories + grille photos."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QStackedWidget, QSizePolicy, QApplication,
    QMessageBox,
)

from bladocommon.database import db
from bladocommon.session import session
from bladocommon.design_system import ds
from bladocommon.theme import theme_manager
from bladocommon.icons import icon as md3_icon
from bladocommon.safe_slot import safe_slot
from bladocommon.widgets.topbar import TopBar


CATEGORIES = [
    # BLADO: catégories RH
    ('dashboard',  "Vue d'ensemble",        0, 0, 'dashboard'),
    ('employees',  'Employés',             0, 0, 'group'),
    ('services',   'Services',             0, 0, 'folder'),
    ('payroll',    'Paie',                 0, 0, 'attach_money'),
    ('letters',    'Courriers',            0, 0, 'subject'),
    ('tasks',      'Tâches',               0, 0, 'check'),
    ('absences',   'Absences/Retards',     0, 0, 'calendar_today'),
    ('missions',   'Missions',             0, 0, 'work'),
    ('settings',   'Paramètres',           0, 0, 'settings'),
]


class _CategoryButton(QPushButton):
    """Bouton de catégorie avec icône + compteur."""

    def __init__(self, key: str, label: str, icon_name: str, parent=None):
        super().__init__(parent)
        self._key = key
        self._label = label
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(theme_manager.image.theme_btn)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        self._restyle_icon()
        self._update_text(0)

    def _restyle_icon(self):
        if self._icon_name:
            try:
                self.setIcon(md3_icon(self._icon_name,
                    color=theme_manager.palette.text_strong, size=18))
            except (ValueError, RuntimeError):
                pass

    def _update_text(self, count: int):
        if count > 0:
            self.setText(f"{self._label} ({count})")
        else:
            self.setText(self._label)

    @property
    def key(self) -> str:
        return self._key


class MainWindow(QWidget):

    SIDEBAR_WIDTH = 233

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blado — Ressources Humaines")
        self._current_key: str | None = None
        self._pages: dict[str, QWidget] = {}

        self._setup_ui()
        self._load_counts()
        ds.theme_changed.connect(self._restyle)

        QTimer.singleShot(100, self._select_first)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar.setStyleSheet(f"""
            #sidebar {{
                background-color: {theme_manager.palette.surface_variant};
                border-right: 1px solid {theme_manager.palette.border};
            }}
        """)

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(ds.space_xs, theme_manager.image.theme_btn,
                                     ds.space_xs, ds.space_lg)
        sb_layout.setSpacing(ds.space_xs)

        # Logo
        import os
        logo_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "photos", "logo.png"),
        ]
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setFixedWidth(int(self.SIDEBAR_WIDTH * 0.9))
        pix = None
        for lp in logo_paths:
            if os.path.exists(lp):
                pix = QPixmap(lp).scaledToWidth(int(self.SIDEBAR_WIDTH * 0.9), Qt.SmoothTransformation)
                break
        if pix and not pix.isNull():
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("Blado")
        logo_lbl.setStyleSheet(
            f"border: none; padding: 0; background: {theme_manager.palette.surface_variant};")
        sb_layout.addWidget(logo_lbl)

        sb_layout.addSpacing(ds.space_xs)

        # "Ressources Humaines" above user
        self._role_label = QLabel("Ressources Humaines")
        self._role_label.setAlignment(Qt.AlignCenter)
        self._role_label.setStyleSheet(f"""
            font-size: {theme_manager.font_size(12)}px;
            color: {theme_manager.palette.text_strong};
            padding: 0 5px;
        """)
        sb_layout.addWidget(self._role_label)

        # User name
        self._user_label = QLabel(session.full_name or "Utilisateur")
        self._user_label.setAlignment(Qt.AlignCenter)
        self._user_label.setStyleSheet(f"""
            font-size: {theme_manager.font_size(12)}px; font-weight: bold;
            color: {theme_manager.palette.text_soft};
            padding: 0 5px 8px 5px;
        """)
        sb_layout.addWidget(self._user_label)

        self._sidebar_sep = QLabel()
        self._sidebar_sep.setFixedHeight(1)
        self._sidebar_sep.setStyleSheet(f"background-color: {theme_manager.palette.border};")
        sb_layout.addWidget(self._sidebar_sep)
        sb_layout.addSpacing(8)

        # Category buttons
        _pal = theme_manager.palette
        _siz = theme_manager.font_size
        self._buttons: dict[str, _CategoryButton] = {}
        for key, label, _lo, _hi, icon_name in CATEGORIES:
            btn = _CategoryButton(key, label, icon_name)
            btn.setStyleSheet(f"""
                QPushButton {{ text-align: center; font-size: {_siz(12)}px;
                color: {_pal.text_strong}; background: transparent;
                border: none; border-radius: {ds.radius_xs}px;
                padding: {ds.space_xxs}px {ds.space_xs}px; }}
                QPushButton:checked {{ background: {_pal.primary_container};
                color: {_pal.text_strong}; font-weight: bold; }}
                QPushButton:hover {{ background: {_pal.surface}; }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._switch_to(k))
            self._buttons[key] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # À propos — même taille que les menus, tout en bas au-dessus du ©
        about_btn = QPushButton("À propos")
        about_btn.setCursor(Qt.PointingHandCursor)
        about_btn.setFixedHeight(theme_manager.image.theme_btn)
        about_btn.setStyleSheet(f"""
            QPushButton {{ text-align: center; font-size: {_siz(12)}px;
            color: {_pal.text_soft}; background: transparent;
            border: none; border-radius: {ds.radius_xs}px;
            padding: {ds.space_xxs}px {ds.space_xs}px; }}
            QPushButton:hover {{ background: {_pal.surface}; color: {_pal.text_strong}; }}
        """)
        about_btn.clicked.connect(self._show_about)
        sb_layout.addWidget(about_btn)
        self._about_btn = about_btn

        # Copyright
        copy_lbl = QLabel("© Bladɔ")
        copy_lbl.setAlignment(Qt.AlignCenter)
        copy_lbl.setStyleSheet(
            f"font-size: {theme_manager.font_size(9)}px; color: {theme_manager.palette.text_soft}; "
            f"border: none; padding-bottom: {ds.space_xs}px;")
        sb_layout.addWidget(copy_lbl)
        self._copy_lbl = copy_lbl

        layout.addWidget(sidebar)
        self._sidebar = sidebar

        # ── Content ──
        self._content = QWidget()
        self._content.setStyleSheet(f"background-color: {theme_manager.palette.background};")
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._topbar = TopBar(show_entreprise=True)
        self._topbar.logout_requested.connect(QApplication.quit)
        self._topbar.theme_changed.connect(self._on_topbar_theme)
        self._topbar.entreprise_changed.connect(self._on_entreprise_changed)
        # BLADO multi-clients : sélecteur visible en mode consultant, client
        # par défaut = première entreprise active
        from Blado.common.blado_database import BladoDatabase
        ent_items = [(e["nom"], e["id"]) for e in BladoDatabase.get_entreprises()]
        self._topbar.set_entreprises(ent_items)
        self._topbar.set_entreprise_visible(session.mode == "consultant")
        if session.mode == "consultant" and ent_items:
            session.entreprise_id = ent_items[0][1]
            self._topbar.select_entreprise(session.entreprise_id)
        cl.addWidget(self._topbar)

        # Header
        self._header = QWidget()
        self._header.setStyleSheet(f"""
            background-color: {theme_manager.palette.surface};
            border-bottom: 1px solid {theme_manager.palette.border};
        """)
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(ds.space_md, ds.space_sm, ds.space_md, ds.space_sm)

        self._section_title = QLabel()
        self._section_title.setStyleSheet(f"""
            font-size: {theme_manager.font_size(16)}px; font-weight: bold;
            color: {theme_manager.palette.text_strong};
        """)
        hl.addWidget(self._section_title)
        hl.addStretch()

        self._add_btn = QPushButton("+ Ajouter")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme_manager.palette.primary}; color: {theme_manager.palette.on_primary};
                border: none; border-radius: {ds.radius_sm}px;
                font-size: {theme_manager.font_size(12)}px; font-weight: bold;
                padding: {ds.space_xs}px {ds.space_md}px;
            }}
            QPushButton:hover {{ background: {theme_manager.palette.primary}; }}
        """)
        self._add_btn.clicked.connect(self._on_add)
        hl.addWidget(self._add_btn)

        cl.addWidget(self._header)

        # Stack
        self._stack = QStackedWidget()
        cl.addWidget(self._stack, 1)

        layout.addWidget(self._content, 1)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _load_counts(self):
        conn = db.server_conn
        if not conn:
            QTimer.singleShot(1000, self._load_counts)
            return
        try:
            cur = conn.cursor()
            for key, _label, lo, hi, _icon in CATEGORIES:
                if key == 'employees':
                    cur.execute("SELECT COUNT(*) FROM blado_employee WHERE is_active = TRUE")
                    cnt = cur.fetchone()[0]
                elif key == 'services':
                    cur.execute("SELECT COUNT(*) FROM services WHERE enabled = TRUE")
                    cnt = cur.fetchone()[0]
                else:
                    continue
                btn = self._buttons.get(key)
                if btn:
                    btn._update_text(cnt)
        except Exception:
            from bladocommon.logger import log
            log("[MainWindow] Impossible de charger les compteurs")

    def _select_first(self):
        for key, _label, _lo, _hi, _icon in CATEGORIES:
            if key in self._buttons:
                self._switch_to(key)
                break

    @safe_slot("MainWindow._switch_to")
    def _switch_to(self, key: str):
        if key == self._current_key:
            return
        self._current_key = key

        for btn in self._buttons.values():
            btn.setChecked(False)
        btn = self._buttons.get(key)
        if btn:
            btn.setChecked(True)
            self._section_title.setText(btn._label)

        # BLADO: bouton "+" visible pour employees, payroll, absences
        self._add_btn.setVisible(key in ('employees', 'absences'))

        if key not in self._pages:
            if key == 'dashboard':
                from Blado.views.dashboard import HRDashboard
                page = HRDashboard()
            elif key == 'payroll':
                from Blado.views.payslip_list import PayslipListPage
                page = PayslipListPage()
            elif key == 'payslip_run':
                from Blado.views.payslip_run import PayslipRunPage
                page = PayslipRunPage()
            elif key == 'letters':
                from Blado.views.letter_manager import LetterManager
                page = LetterManager()
            elif key == 'tasks':
                page = self._make_todo_page()
            elif key == 'absences':
                from Blado.views.absence_planner import AbsencePlanner
                page = AbsencePlanner()
            elif key == 'settings':
                from Blado.views.settings_page import SettingsPage
                page = SettingsPage()
            elif key == 'missions':
                from Blado.views.mission_dialog import MissionPage
                page = MissionPage()
            elif key == 'services':
                from Blado.views.service_page import ServicePage
                page = ServicePage()
            elif key == 'employees':
                from Blado.views.staff_grid import StaffGrid
                page = StaffGrid(key, 0, 0, is_staff=False)
                page.staff_selected.connect(self._show_detail)
            else:
                from Blado.views.staff_grid import StaffGrid
                page = StaffGrid(key, 0, 0, is_staff=False)
                page.staff_selected.connect(self._show_detail)
            self._pages[key] = page
            self._stack.addWidget(page)

        self._stack.setCurrentWidget(self._pages[key])
        page = self._pages[key]
        if hasattr(page, 'refresh'):
            page.refresh()

    @safe_slot("MainWindow._show_detail")
    def _show_detail(self, staff_data: dict):
        from Blado.views.staff_detail import StaffDetail
        detail = StaffDetail(staff_data, on_back=self._on_back_from_detail)
        self._stack.addWidget(detail)
        self._stack.setCurrentWidget(detail)

    @safe_slot("MainWindow._on_back_from_detail")
    def _on_back_from_detail(self):
        # Remove all detail widgets (they're pushed on top of the stack)
        from Blado.views.staff_detail import StaffDetail
        for i in range(self._stack.count() - 1, -1, -1):
            w = self._stack.widget(i)
            if isinstance(w, StaffDetail):
                self._stack.removeWidget(w)
                w.deleteLater()
        if self._current_key and self._current_key in self._pages:
            self._stack.setCurrentWidget(self._pages[self._current_key])
            # Rafraîchir la page restaurée (photo/modifs faites dans la fiche)
            page = self._pages[self._current_key]
            if hasattr(page, "refresh"):
                page.refresh()

    def _make_todo_page(self):
        from bladocommon.widgets.todo_kanban import TodoKanban
        from Blado.common.blado_database import BladoDatabase
        from bladocommon.session import session
        BladoDatabase.ensure_todo_table()
        kanban = TodoKanban(
            load_fn=BladoDatabase.get_todos,
            create_fn=BladoDatabase.create_todo,
            move_fn=BladoDatabase.move_todo,
            delete_fn=BladoDatabase.delete_todo,
            reopen_fn=lambda task, uid: BladoDatabase.create_todo(
                task.get("desc", ""), task.get("type", "custom"),
                task.get("due_date"), task.get("staff_id"), uid),
            task_types={
                "recrutement": "Recrutement",
                "contrat":    "Contrat",
                "paie":       "Paie",
                "formation":  "Formation",
                "evaluation": "Évaluation",
                "disciplinaire": "Disciplinaire",
                "conge":      "Congé",
                "document":   "Document",
                "custom":     "Manuel",
            },
            user_id=session.user_id,
        )
        return kanban

    @safe_slot("MainWindow._on_add")
    def _on_add(self):
        if self._current_key in ('dashboard', 'letters', 'tasks', 'payroll', 'settings', 'services'):
            return
        if self._current_key == 'absences':
            from Blado.views.staff_events import open_staff_event_generator
            open_staff_event_generator(None, parent=self)
            # Refresh absence planner after dialog closes
            if self._current_key in self._pages:
                page = self._pages[self._current_key]
                if hasattr(page, 'refresh'):
                    page.refresh()
            return
        from Blado.views.staff_form import StaffFormDialog
        from Blado.common.blado_database import BladoDatabase
        # BLADO: trouver le 1er slot libre dans le 1er service actif
        active_svcs = [s for s in BladoDatabase.get_services() if s.get("enabled")]
        slot_id = None
        for svc in active_svcs:
            slots = BladoDatabase.get_free_slots(svc["id"])
            if slots:
                slot_id = slots[0]["id"]
                break
        dlg = StaffFormDialog(0, 0, slot_id=slot_id, parent=self)
        if dlg.exec():
            self._load_counts()
            QMessageBox.information(self, "Blado", "Employé enregistré.")
            if self._current_key in self._pages:
                page = self._pages[self._current_key]
                if hasattr(page, 'refresh'):
                    page.refresh()

    @safe_slot("MainWindow._show_about")
    def _show_about(self):
        from PySide6.QtWidgets import QDialog, QLabel, QPushButton
        p = theme_manager.palette
        dlg = QDialog(self)
        dlg.setWindowTitle("À propos de Blado")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(ds.space_md)
        layout.setContentsMargins(ds.space_xl, ds.space_xl, ds.space_xl, ds.space_xl)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "photos", "LogoBlado.png")
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        if os.path.exists(logo_path):
            logo_lbl.setPixmap(QPixmap(logo_path).scaledToWidth(120, Qt.SmoothTransformation))
        logo_lbl.setStyleSheet("border:none;")
        layout.addWidget(logo_lbl)

        title = QLabel("Bladɔ — Logiciel de Gestion RH")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size:{ds.font_h2}px;font-weight:bold;color:{p.text_strong};border:none;")
        layout.addWidget(title)

        info = QLabel(
            "1. Qu'est-ce que Bladɔ ?\n"
            "Blado est un logiciel de gestion des ressources humaines "
            "concus pour les entreprises et les cabinets de conseil RH "
            "operant au Togo et en Afrique de l'Ouest.\n\n"
            "2. Sa mission\n"
            "Simplifier et securiser la gestion administrative du personnel "
            "tout en respectant le cadre legal togolais (CNSS, Code du Travail). "
            "Blado couvre le cycle de vie complet de l'employe : embauche, "
            "contrats, conges, paie, discipline et depart.\n\n"
            "3. Open Source\n"
            "github.com/yaoplab/Blad-\n"
            "Licence MIT. PySide6 + PostgreSQL.\n"
            "Contributions bienvenues !")
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size:{ds.font_body}px;color:{p.text_soft};border:none;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        close_btn = QPushButton("Fermer")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        close_btn.setStyleSheet(f"background:{p.primary};color:{p.on_primary};font-weight:bold;"
                               f"border:none;border-radius:{ds.radius_sm}px;"
                               f"padding:{ds.space_xs}px {ds.space_md}px;")
        layout.addWidget(close_btn, 0, Qt.AlignCenter)
        # no-popup-feedback : dialogue purement informatif (À propos)
        dlg.exec()

    @safe_slot("MainWindow._restyle")
    @safe_slot("MainWindow._on_topbar_theme")
    def _on_topbar_theme(self, key: str):
        theme_manager.set_active(key)
        session.theme_pref = key
        self._restyle()

    @safe_slot("MainWindow._on_entreprise_changed")
    def _on_entreprise_changed(self, eid: int):
        # BLADO multi-clients : le client actif pilote paie, missions,
        # dashboard, absences et courriers (0 = toutes les entreprises)
        session.entreprise_id = eid or 0
        if self._current_key and self._current_key in self._pages:
            page = self._pages[self._current_key]
            if hasattr(page, "refresh"):
                page.refresh()

    def _restyle(self):
        p = theme_manager.palette
        s = theme_manager.font_size
        try:
            self._sidebar.setStyleSheet(f"""
                #sidebar {{
                    background-color: {p.surface_variant};
                    border-right: 1px solid {p.border};
                }}
            """)
            self._content.setStyleSheet(f"background-color: {p.background};")
            self._header.setStyleSheet(f"""
                background-color: {p.surface};
                border-bottom: 1px solid {p.border};
            """)
            self._role_label.setStyleSheet(f"""
                font-size: {s(10)}px; color: {p.text_strong}; padding: 0 5px;
            """)
            self._user_label.setStyleSheet(f"""
                font-size: {s(12)}px; font-weight: bold;
                color: {p.text_soft}; padding: 0 5px 8px 5px;
            """)
            self._sidebar_sep.setStyleSheet(f"background-color: {p.border};")
            self._about_btn.setStyleSheet(f"""
                QPushButton {{ text-align: center; font-size: {s(12)}px;
                color: {p.text_soft}; background: transparent;
                border: none; border-radius: {ds.radius_xs}px;
                padding: {ds.space_xxs}px {ds.space_xs}px; }}
                QPushButton:hover {{ background: {p.surface}; color: {p.text_strong}; }}
            """)
            self._copy_lbl.setStyleSheet(
                f"font-size: {s(9)}px; color: {p.text_soft}; "
                f"border: none; padding-bottom: {ds.space_xs}px;")
            self._section_title.setStyleSheet(f"""
                font-size: {s(16)}px; font-weight: bold; color: {p.text_strong};
            """)
            self._add_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {p.primary}; color: {p.on_primary};
                    border: none; border-radius: {ds.radius_sm}px;
                    font-size: {s(12)}px; font-weight: bold;
                    padding: {ds.space_xs}px {ds.space_md}px;
                }}
                QPushButton:hover {{ background: {p.primary}; }}
            """)
            # Boutons de catégorie — QSS complet
            for btn in self._buttons.values():
                btn.setStyleSheet(f"""
                    QPushButton {{ text-align: center; font-size: {s(12)}px;
                    color: {p.text_strong}; background: transparent;
                    border: none; border-radius: {ds.radius_xs}px;
                    padding: {ds.space_xxs}px {ds.space_xs}px; }}
                    QPushButton:checked {{ background: {p.primary_container};
                    color: {p.text_strong}; font-weight: bold; }}
                    QPushButton:hover {{ background: {p.surface}; }}
                """)
                btn._restyle_icon()
            if hasattr(self, "_topbar"):
                self._topbar.restyle()
        except RuntimeError:
            pass
