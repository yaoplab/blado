# BladoHRMixin — méthodes RH extraites de BladoDatabase
# BLADO: fichier ≤ 1000 lignes (règle pyside6-wrapper)

from __future__ import annotations
import json
from typing import Any
from datetime import date, datetime
from bladocommon.database import db


def _ent_filter(emp: str = "a", srv: str = "s") -> str:
    """BLADO multi-clients : fragment WHERE commun — un employé est rattaché à
    son client directement (fk_entreprise_id) ou via son service
    (services.entreprise_id) quand la colonne n'est pas encore remplie."""
    return (f"({emp}.fk_entreprise_id = %s OR "
            f"({emp}.fk_entreprise_id IS NULL AND {srv}.entreprise_id = %s))")


# Alias a/s par défaut (le plus courant)
ENT_FILTER_SQL = _ent_filter()

class BladoHRMixin:

    # ========================================================================
    # Services — gestion des services et gabarits
    # ========================================================================

    @staticmethod
    def get_services() -> list[dict[str, Any]]:
        """Liste des services avec compteurs d'employés."""
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.label, s.code, s.color, s.description, s.sort_order, s.enabled,
                   s.entreprise_id, ent.nom AS entreprise_nom,
                   COUNT(e.id) FILTER (WHERE e.is_active = TRUE) AS active_count,
                   COUNT(e.id) AS total_slots
            FROM services s
            LEFT JOIN entreprises ent ON ent.id = s.entreprise_id
            LEFT JOIN blado_employee e ON e.fk_service_id = s.id
            GROUP BY s.id, ent.nom ORDER BY s.id
        """)
        cols = ["id", "label", "code", "color", "description", "sort_order", "enabled",
                "entreprise_id", "entreprise_nom",
                "active_count", "total_slots"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def create_service(data: dict) -> int | None:
        """Active/modifie un service (UPDATE — jamais INSERT)."""
        conn = db.server_conn
        if not conn: return None
        try:
            cur = conn.cursor()
            sid = data["id"]
            enabled = data.get("enabled", True)
            cur.execute(
                "UPDATE services SET label=%s, code=%s, description=%s, color=%s, "
                "enabled=%s, entreprise_id=%s WHERE id=%s",
                (data["label"], data.get("code", ""), data.get("description", ""),
                 data.get("color", "white"), enabled, data.get("entreprise_id"), sid))
            # BLADO multi-clients : les employés actifs du service héritent du
            # client qui vient d'être rattaché (fk_entreprise_id synchronisé).
            cur.execute("""
                UPDATE blado_employee SET fk_entreprise_id = %s, updated_at=NOW()
                WHERE fk_service_id = %s AND is_active = TRUE
                  AND (fk_entreprise_id IS NULL OR fk_entreprise_id <> %s)
            """, (data.get("entreprise_id"), sid, data.get("entreprise_id")))
            return sid
        except Exception:
            return None

    @staticmethod
    def create_service_gabarit(service_id: int, nb_slots: int = 99) -> int:
        conn = db.server_conn
        if not conn: return 0
        try:
            cur = conn.cursor()
            id_start = service_id * 100 + 1
            id_end = service_id * 100 + nb_slots
            cur.execute("""
                INSERT INTO blado_employee (id, fk_service_id, first_name, last_name,
                    is_active, emp_status)
                SELECT s, %s, 'Employé', 'ID' || s::TEXT, FALSE, 'inactif'
                FROM generate_series(%s, %s) AS s
                WHERE NOT EXISTS (SELECT 1 FROM blado_employee WHERE id = s)
            """, (service_id, id_start, id_end))
            return cur.rowcount
        except Exception:
            return 0

    @staticmethod
    def delete_service(service_id: int) -> bool:
        conn = db.server_conn
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM services WHERE id = %s", (service_id,))
            return True
        except Exception:
            return False

    @staticmethod
    def get_free_slots(service_id: int) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        # Seuls les EMPLACEMENTS (lignes placeholder 'Employe'/'Slot XXXXX') sont
        # des slots libres. Un vrai employé désactivé ne doit JAMAIS être écrasé
        # par une création (bug 2026-08-13 : 2 employés détruits).
        cur.execute("""
            SELECT id, first_name, last_name FROM blado_employee
            WHERE fk_service_id = %s AND is_active = FALSE
              AND first_name IN ('Employe', 'Employé') AND last_name LIKE 'Slot %%'
            ORDER BY id LIMIT 50
        """, (service_id,))
        return [{"id": r[0], "first_name": r[1], "last_name": r[2]} for r in cur.fetchall()]

    @staticmethod
    def activate_employee(slot_id: int, data: dict) -> int | None:
        conn = db.server_conn
        if not conn: return None
        try:
            cur = conn.cursor()
            # Garde-fou : n'activer QUE des emplacements placeholder — jamais
            # un vrai employé désactivé (risque d'écrasement de données).
            cur.execute("""
                UPDATE blado_employee SET
                    first_name=%s, last_name=%s, email=%s, phone_mobile=%s,
                    fk_service_id=COALESCE(%s, fk_service_id),
                    -- BLADO multi-clients : le client de l'employé suit son
                    -- service (services.entreprise_id) — jamais mélangé entre clients
                    fk_entreprise_id=(SELECT s.entreprise_id FROM services s
                                      WHERE s.id = COALESCE(%s, fk_service_id)),
                    civility=%s, nationality=%s, marital_status=%s, children_count=%s,
                    emergency_contact_name=%s, emergency_contact_phone=%s,
                    blood_type=%s, cnss_number=%s, tax_id=%s,
                    id_document_type=%s, id_document_number=%s, id_document_expiry=%s,
                    matricule=%s, professional_category=%s,
                    hire_date=%s, emp_status='actif',
                    is_active=TRUE, updated_at=NOW()
                WHERE id=%s AND is_active=FALSE
                  AND first_name IN ('Employe', 'Employé') AND last_name LIKE 'Slot %%'
            """, (data.get("first_name",""), data.get("last_name",""), data.get("email",""),
                  data.get("phone_mobile",""), data.get("fk_service_id"),
                  data.get("fk_service_id"),
                  data.get("civility",""),
                  data.get("nationality",""), data.get("marital_status",""),
                  data.get("children_count",0),
                  data.get("emergency_contact_name",""), data.get("emergency_contact_phone",""),
                  data.get("blood_type",""), data.get("cnss_number",""), data.get("tax_id",""),
                  data.get("id_document_type",""), data.get("id_document_number",""),
                  data.get("id_document_expiry"),
                  data.get("matricule",""), data.get("professional_category",""),
                  data.get("hire_date"),
                  slot_id))
            if cur.rowcount == 0:
                return None
            if data.get("contract_type"):
                cur.execute("""
                    INSERT INTO blado_contract (staff_id, contract_type, date_debut,
                        date_fin, periode_essai, salaire_brut, volume_horaire, statut)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'actif')
                """, (slot_id, data["contract_type"], data.get("date_debut"),
                      data.get("date_fin"), data.get("periode_essai"),
                      data.get("salaire_brut",0), data.get("volume_horaire")))
            cur.execute("""
                INSERT INTO blado_leave_balance (staff_id, year, leave_type, total_days, used_days)
                VALUES (%s,%s,'CA',30,0)
                ON CONFLICT (staff_id, year, leave_type) DO NOTHING
            """, (slot_id, date.today().year))
            return slot_id
        except Exception:
            return None
    @staticmethod
    def get_trial_periods_ending(entreprise_id: int | None = None) -> int:
        """Périodes d'essai se terminant dans les 15 jours (filtré par client)."""
        conn = db.server_conn
        if not conn: return 0
        try:
            cur = conn.cursor()
            query = """
                SELECT COUNT(*) FROM blado_contract c
                JOIN blado_employee a ON a.id = c.staff_id
                LEFT JOIN services s ON s.id = a.fk_service_id
                WHERE c.statut = 'actif' AND c.periode_essai_fin IS NOT NULL
                  AND c.periode_essai_fin BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '15 days'
            """
            params: list[Any] = []
            if entreprise_id:
                query += f" AND {ENT_FILTER_SQL}"
                params = [entreprise_id, entreprise_id]
            cur.execute(query, params)
            return cur.fetchone()[0] or 0
        except Exception:
            return 0

    @staticmethod
    def get_missing_fields_stats(entreprise_id: int | None = None) -> list[dict[str, Any]]:
        """Top 5 des champs les plus souvent manquants (filtré par client)."""
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        try:
            fields = [
                ("N° CNSS", "cnss_number"),
                ("Matricule", "matricule"),
                ("Contact urgence (nom)", "emergency_contact_name"),
                ("Contact urgence (tél)", "emergency_contact_phone"),
                ("Pièce d'identité", "id_document_number"),
                ("Date de naissance", "hire_date"),
                ("Nationalité", "nationality"),
                ("Situation familiale", "marital_status"),
            ]
            ent_where = f" AND {ENT_FILTER_SQL}" if entreprise_id else ""
            ent_params = (entreprise_id, entreprise_id) if entreprise_id else ()
            result = []
            for label, col in fields:
                # DATE columns can't be compared to ''
                if col == 'hire_date':
                    cond = f"{col} IS NULL"
                else:
                    cond = f"({col} IS NULL OR {col} = '')"
                cur.execute(f"""
                    SELECT COUNT(*) FROM blado_employee a
                    LEFT JOIN services s ON s.id = a.fk_service_id
                    WHERE a.emp_status = 'actif' AND a.departure_date IS NULL
                      AND {cond}
                    {ent_where}
                """, ent_params)
                missing = cur.fetchone()[0] or 0
                result.append({"label": label, "missing": missing})
            result.sort(key=lambda x: x["missing"], reverse=True)
            return result[:5]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_missing_docs_stats(entreprise_id: int | None = None) -> list[dict[str, Any]]:
        """Employés actifs sans document (filtré par client)."""
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        try:
            # Compte les employés sans aucun document
            query = """
                SELECT COUNT(*) FROM blado_employee a
                LEFT JOIN services s ON s.id = a.fk_service_id
                WHERE a.emp_status = 'actif' AND a.is_active = TRUE
                AND NOT EXISTS (SELECT 1 FROM blado_document d WHERE d.staff_id = a.id)
            """
            params: list[Any] = []
            if entreprise_id:
                query += f" AND {ENT_FILTER_SQL}"
                params = [entreprise_id, entreprise_id]
            cur.execute(query, params)
            missing = cur.fetchone()[0] or 0
            result = [{"label": "Sans documents", "missing": missing}]
            result.sort(key=lambda x: x["missing"], reverse=True)
            return result
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_professional_categories() -> list[str]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute("""
            SELECT label_fr FROM blado_professional_category
            WHERE enabled = true ORDER BY is_education DESC, label_fr
        """)
        return [r[0] for r in cur.fetchall()]

    # ========================================================================
    # Missions (consultant)
    # ========================================================================

    @staticmethod
    def get_missions(entreprise_id: int | None = None) -> list[dict]:
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        q = """SELECT m.*, c.nom AS consultant_nom, e.nom AS entreprise_nom
               FROM missions m
               JOIN consultants c ON c.id=m.consultant_id
               JOIN entreprises e ON e.id=m.entreprise_id
               WHERE 1=1"""
        params = []
        if entreprise_id:
            q += " AND m.entreprise_id=%s"; params.append(entreprise_id)
        q += " ORDER BY m.date_debut DESC"
        cur.execute(q, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def get_mission(id: int) -> dict | None:
        conn = db.server_conn
        if not conn: return None
        cur = conn.cursor()
        cur.execute("""SELECT m.*, c.nom AS consultant_nom, e.nom AS entreprise_nom
                       FROM missions m
                       JOIN consultants c ON c.id=m.consultant_id
                       JOIN entreprises e ON e.id=m.entreprise_id
                       WHERE m.id=%s""", (id,))
        r = cur.fetchone()
        if not r: return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, r))

    @staticmethod
    def save_mission(data: dict) -> int | None:
        conn = db.server_conn
        if not conn: return None
        try:
            cur = conn.cursor()
            if data.get("id"):
                cur.execute("""UPDATE missions SET consultant_id=%s, entreprise_id=%s,
                    reference=%s, type_mission=%s, titre=%s, description=%s,
                    date_debut=%s, date_fin=%s, date_signature=%s,
                    montant=%s, devise=%s, periodicite=%s, modalites_paiement=%s,
                    gerer_paie=%s, gerer_contrats=%s, gerer_conges=%s,
                    gerer_recrutement=%s, gerer_formations=%s, gerer_discipline=%s,
                    gerer_documents=%s, statut=%s, delai_preavis_jours=%s,
                    notes=%s, updated_at=NOW()
                    WHERE id=%s""",
                    (data["consultant_id"], data["entreprise_id"],
                     data.get("reference",""), data.get("type_mission",""), data.get("titre",""),
                     data.get("description",""), data.get("date_debut"), data.get("date_fin"),
                     data.get("date_signature"), data.get("montant"), data.get("devise","XOF"),
                     data.get("periodicite",""), data.get("modalites_paiement",""),
                     data.get("gerer_paie",False), data.get("gerer_contrats",False),
                     data.get("gerer_conges",False), data.get("gerer_recrutement",False),
                     data.get("gerer_formations",False), data.get("gerer_discipline",False),
                     data.get("gerer_documents",False), data.get("statut","active"),
                     data.get("delai_preavis_jours",30), data.get("notes",""), data["id"]))
                return data["id"]
            else:
                cur.execute("""INSERT INTO missions (consultant_id, entreprise_id,
                    reference, type_mission, titre, description, date_debut, date_fin,
                    date_signature, montant, devise, periodicite, modalites_paiement,
                    gerer_paie, gerer_contrats, gerer_conges, gerer_recrutement,
                    gerer_formations, gerer_discipline, gerer_documents,
                    statut, delai_preavis_jours, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id""",
                    (data["consultant_id"], data["entreprise_id"],
                     data.get("reference",""), data.get("type_mission",""), data.get("titre",""),
                     data.get("description",""), data.get("date_debut"), data.get("date_fin"),
                     data.get("date_signature"), data.get("montant"), data.get("devise","XOF"),
                     data.get("periodicite",""), data.get("modalites_paiement",""),
                     data.get("gerer_paie",False), data.get("gerer_contrats",False),
                     data.get("gerer_conges",False), data.get("gerer_recrutement",False),
                     data.get("gerer_formations",False), data.get("gerer_discipline",False),
                     data.get("gerer_documents",False), data.get("statut","active"),
                     data.get("delai_preavis_jours",30), data.get("notes","")))
                return cur.fetchone()[0]
        except Exception:
            import traceback; traceback.print_exc()
            return None

    @staticmethod
    def get_missions_kpis(entreprise_id: int | None = None) -> dict:
        conn = db.server_conn
        if not conn: return {}
        cur = conn.cursor()
        query = ("SELECT COUNT(*) FILTER (WHERE statut='active'), COUNT(*), "
                 "COALESCE(SUM(montant),0) FROM missions")
        params: list[Any] = []
        if entreprise_id:
            query += " WHERE entreprise_id=%s"
            params.append(entreprise_id)
        cur.execute(query, params)
        r = cur.fetchone()
        return {"actives": r[0] or 0, "total": r[1] or 0, "montant_total": float(r[2] or 0)}

    @staticmethod
    def get_consultants() -> list[dict]:
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        cur.execute("SELECT id, nom, telephone, email, est_actif FROM consultants WHERE est_actif=TRUE ORDER BY nom")
        return [{"id": r[0], "nom": r[1], "telephone": r[2], "email": r[3], "est_actif": r[4]} for r in cur.fetchall()]

    @staticmethod
    def get_entreprises() -> list[dict]:
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        cur.execute("SELECT id, nom, telephone, email, ville, est_active FROM entreprises ORDER BY nom")
        return [{"id": r[0], "nom": r[1], "telephone": r[2], "email": r[3], "ville": r[4], "est_active": r[5]} for r in cur.fetchall()]

    # ========================================================================
    # Consultants & entreprises — CRUD complet (page Paramètres)
    # ========================================================================

    _CONSULTANT_FIELDS = [
        "nom", "sigle", "forme_juridique", "matricule_fiscal",
        "telephone", "whatsapp", "email", "site_web",
        "adresse", "code_postal", "ville", "pays",
        "signature_nom", "signature_titre", "logo_path",
        "est_actif", "notes",
    ]

    _ENTREPRISE_FIELDS = [
        "nom", "sigle", "forme_juridique", "registre_commerce", "id_fiscal",
        "telephone", "whatsapp", "email", "site_web",
        "facebook", "linkedin", "twitter",
        "adresse", "code_postal", "ville", "pays",
        "logo_path", "est_active", "is_self", "notes", "color",
    ]

    @staticmethod
    def _save_row(table: str, fields: list[str], data: dict) -> int | None:
        conn = db.server_conn
        if not conn: return None
        try:
            cur = conn.cursor()
            vals = [data.get(f, "") for f in fields]
            if data.get("id"):
                sets = ", ".join(f"{f}=%s" for f in fields) + ", updated_at=NOW()"
                cur.execute(f"UPDATE {table} SET {sets} WHERE id=%s",
                            vals + [data["id"]])
                return data["id"]
            ph = ", ".join(["%s"] * len(fields))
            cur.execute(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({ph}) RETURNING id", vals)
            return cur.fetchone()[0]
        except Exception:
            import traceback; traceback.print_exc()
            return None

    @staticmethod
    def get_consultants_full() -> list[dict]:
        """Tous les consultants (actifs et inactifs) — gestion page Paramètres."""
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        cur.execute("SELECT * FROM consultants ORDER BY nom")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def save_consultant(data: dict) -> int | None:
        return BladoHRMixin._save_row("consultants", BladoHRMixin._CONSULTANT_FIELDS, data)

    @staticmethod
    def get_entreprises_full() -> list[dict]:
        """Toutes les entreprises clientes (actives et inactives)."""
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        cur.execute("SELECT * FROM entreprises ORDER BY is_self DESC, nom")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def save_entreprise(data: dict) -> int | None:
        return BladoHRMixin._save_row("entreprises", BladoHRMixin._ENTREPRISE_FIELDS, data)

    @staticmethod
    def get_first_disabled_service() -> dict | None:
        """Retourne le premier service avec enabled=FALSE (pour activation)."""
        conn = db.server_conn
        if not conn: return None
        cur = conn.cursor()
        cur.execute("SELECT id, label, code, description, color, enabled FROM services WHERE enabled = FALSE ORDER BY id LIMIT 1")
        r = cur.fetchone()
        if not r: return None
        return {"id": r[0], "label": r[1], "code": r[2], "description": r[3], "color": r[4], "enabled": r[5]}

    @staticmethod
    def get_service_full(service_id: int) -> dict[str, Any] | None:
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            SELECT id, label, adress, city, country, tel_1, email_1
            FROM services WHERE id = %s
        """, (service_id,))
        r = cur.fetchone()
        if not r:
            return None
        cols = ["id", "label", "adress", "city", "country", "tel_1", "email_1"]
        return dict(zip(cols, r))

    @staticmethod
    def get_available_supervisors(service_id: int | None = None) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        query = """
            SELECT id, first_name, last_name
            FROM blado_employee
            WHERE is_active = TRUE
        """
        params: list[Any] = []
        if service_id:
            query += " AND fk_service_id = %s"
            params.append(service_id)
        query += " ORDER BY last_name, first_name"
        cur.execute(query, params)
        return [{"id": r[0], "full_name": f"{r[2]} {r[1]}"} for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_staff(row: tuple) -> dict[str, Any]:
        # 28 colonnes: id,first,last,email,phone_home,phone_mobile,personal_email,
        # hire_date,is_active,civility,nationality,marital_status,children_count,
        # emergency_contact_name,emergency_contact_phone,blood_type,cnss_number,
        # tax_id,id_document_type,id_document_number,id_document_expiry,
        # matricule,professional_category,emp_status,departure_date,
        # departure_reason,fk_service_id,fk_supervisor_id
        return {
            "id": row[0], "first_name": row[1], "last_name": row[2], "email": row[3],
            "phone_home": row[4], "phone_mobile": row[5], "personal_email": row[6],
            "hire_date": row[7], "is_active": row[8],
            "civility": row[9], "nationality": row[10], "marital_status": row[11],
            "children_count": row[12], "emergency_contact_name": row[13],
            "emergency_contact_phone": row[14], "blood_type": row[15],
            "cnss_number": row[16], "tax_id": row[17],
            "id_document_type": row[18], "id_document_number": row[19],
            "id_document_expiry": row[20], "matricule": row[21],
            "professional_category": row[22], "emp_status": row[23],
            "departure_date": row[24], "departure_reason": row[25],
            "fk_service_id": row[26], "fk_supervisor_id": row[27],
            "full_name": f"{row[2]} {row[1]}",
        }

    @staticmethod
    def _row_to_staff_compact(row: tuple, is_staff: bool) -> dict[str, Any]:
        # BLADO: 0=id,1=first,2=last,3=email,4=emp_status,
        # 5=fk_service_id,6=pro_cat,7=matricule,8=service_label,9=service_color,
        # 10=entreprise_nom
        return {
            "id": row[0], "first_name": row[1], "last_name": row[2],
            "email": row[3], "full_name": f"{row[2]} {row[1]}",
            "emp_status": row[4], "fk_service_id": row[5],
            "professional_category": row[6], "matricule": row[7],
            "service_label": row[8], "service_color": row[9],
            "entreprise_nom": row[10],
        }

    # ------------------------------------------------------------------
    # Detail categories (sidebar dynamique)
    # ------------------------------------------------------------------

    @staticmethod
    def get_detail_categories() -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return _FALLBACK_CATEGORIES
        cur = conn.cursor()
        cur.execute("""
            SELECT category_key, label_fr, icon_name, sort_order
            FROM blado_detail_category
            WHERE enabled = true ORDER BY sort_order
        """)
        rows = cur.fetchall()
        if not rows:
            return _FALLBACK_CATEGORIES
        return [
            {"key": r[0], "label": r[1], "icon": r[2], "order": r[3]}
            for r in rows
        ]

    @staticmethod
    def add_detail_category(category_key: str, label_fr: str,
                            icon_name: str = "folder") -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM blado_detail_category")
            next_order = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO blado_detail_category (category_key, label_fr, icon_name, sort_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (category_key) DO UPDATE SET enabled = true, label_fr = %s, icon_name = %s
            """, (category_key, label_fr, icon_name, next_order, label_fr, icon_name))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def delete_detail_category(category_key: str) -> tuple[bool, str]:
        """Supprime une categorie. Retourne (ok, message). Refuse si documents associes."""
        conn = db.server_conn
        if not conn:
            return False, "Base de donnees non disponible"
        cur = conn.cursor()

        # NB : blado_document n'a plus de colonne category_key (documents par
        # label, non catégorisés) — la vérification d'usage a été retirée.

        cur.execute(
            "UPDATE blado_detail_category SET enabled = false WHERE category_key = %s",
            (category_key,))
        return True, ""

    # ------------------------------------------------------------------
    # Documents (métadonnées)
    # ------------------------------------------------------------------

    @staticmethod
    def get_documents(staff_id: int) -> list[dict]:
        """Liste tous les documents d'un employé."""
        conn = db.server_conn
        if not conn: return []
        cur = conn.cursor()
        cur.execute("""
            SELECT id, label, description, file_path, url, file_size, uploaded_at
            FROM blado_document WHERE staff_id=%s ORDER BY uploaded_at DESC
        """, (staff_id,))
        cols = ["id", "label", "description", "file_path", "url", "file_size", "uploaded_at"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def save_document(staff_id: int, label: str, description: str,
                      file_path: str = "", url: str = "", file_size: int = 0) -> bool:
        """Ajoute ou met à jour un document (UPSERT sur staff_id+label)."""
        conn = db.server_conn
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO blado_document (staff_id, label, description, file_path, url, file_size)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (staff_id, label)
                DO UPDATE SET description=%s, file_path=%s, url=%s, file_size=%s, uploaded_at=NOW()
            """, (staff_id, label, description, file_path, url, file_size,
                  description, file_path, url, file_size))
            return True
        except Exception:
            import traceback; traceback.print_exc()
            return False

    @staticmethod
    def delete_document(doc_id: int) -> bool:
        """Supprime un document par son ID."""
        conn = db.server_conn
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM blado_document WHERE id=%s", (doc_id,))
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Letters — Modèles et courriers générés
    # ------------------------------------------------------------------

    @staticmethod
    def get_letter_templates(family: str | None = None,
                             search: str = "",
                             active_only: bool = True) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        query = """
            SELECT id, family, code, title, description,
                   body_text, source_code,
                   COALESCE(variables, '{}') AS variables,
                   version, is_active, is_builtin, created_at
            FROM blado_letter_template
        """
        conditions: list[str] = []
        params: list[Any] = []
        if active_only:
            conditions.append("is_active = TRUE")
        if family:
            conditions.append("family = %s")
            params.append(family)
        if search:
            conditions.append("(title ILIKE %s OR description ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY is_builtin ASC, family, code"
        cur.execute(query, params)
        cols = ["id", "family", "code", "title", "description",
                "body_text", "source_code",
                "variables", "version", "is_active", "is_builtin", "created_at"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def get_letter_template_by_id(template_id: int) -> dict[str, Any] | None:
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            SELECT id, family, code, title, description, docx_data,
                   body_text, source_code,
                   COALESCE(variables, '{}') AS variables,
                   version, is_active, is_builtin, created_at
            FROM blado_letter_template WHERE id = %s
        """, (template_id,))
        r = cur.fetchone()
        if not r:
            return None
        cols = ["id", "family", "code", "title", "description", "docx_data",
                "body_text", "source_code",
                "variables", "version", "is_active", "is_builtin", "created_at"]
        return dict(zip(cols, r))

    @staticmethod
    def save_letter_template(data: dict[str, Any]) -> int | None:
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        try:
            if data.get("id"):
                sets = [
                    "title = %s", "description = %s", "docx_data = %s",
                    "variables = %s", "version = version + 1", "updated_at = NOW()",
                ]
                params: list[Any] = [
                    data["title"], data.get("description"), data.get("docx_data"),
                    data.get("variables", []),
                ]
                # body_text : écrit seulement si la clé est présente ; clear_body
                # force NULL (restauration vers le corps fonction d'origine)
                if "body_text" in data:
                    sets.append("body_text = %s")
                    params.append(data["body_text"])
                elif data.get("clear_body"):
                    sets.append("body_text = NULL")
                # source_code : écrit seulement si la clé est présente
                if "source_code" in data:
                    sets.append("source_code = %s")
                    params.append(data["source_code"])
                cur.execute(
                    f"UPDATE blado_letter_template SET {', '.join(sets)} "
                    "WHERE id = %s AND NOT is_builtin",
                    params + [data["id"]])
                return data["id"]
            else:
                cur.execute("""
                    INSERT INTO blado_letter_template (family, code, title, description,
                        body_text, source_code,
                        docx_data, variables, is_builtin, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s)
                    RETURNING id
                """, (data.get("family", "F"), data.get("code", ""), data["title"],
                      data.get("description"), data.get("body_text"),
                      data.get("source_code"), data.get("docx_data"),
                      data.get("variables", []), data.get("created_by")))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def toggle_letter_template(template_id: int, active: bool) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute("UPDATE blado_letter_template SET is_active = %s, updated_at = NOW() WHERE id = %s",
                    (active, template_id))
        return True

    @staticmethod
    def save_generated_letter(staff_id: int, template_id: int, file_path: str,
                              reference: str = "", generated_by: int | None = None) -> int | None:
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        try:
            # created_by référence blado_employee — l'utilisateur connecté
            # (blado_user) n'y correspond pas forcément → NULL sinon FK violée
            generated_by = generated_by or None
            if generated_by:
                cur.execute("SELECT 1 FROM blado_employee WHERE id = %s", (generated_by,))
                if not cur.fetchone():
                    generated_by = None
            cur.execute("""
                INSERT INTO blado_generated_letter (staff_id, template_id, file_path, reference, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (staff_id, template_id, file_path, reference, generated_by))
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def get_generated_letters(staff_id: int | None = None,
                              limit: int = 50) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        query = """
            SELECT g.id, g.staff_id, g.template_id, g.file_path, g.reference,
                   g.generated_at, g.generated_by, g.status,
                   t.title AS template_title, t.family, t.code,
                   a.first_name, a.last_name
            FROM blado_generated_letter g
            JOIN blado_letter_template t ON t.id = g.template_id
            JOIN blado_employee a ON a.id = g.staff_id
        """
        params: list[Any] = []
        if staff_id is not None:
            query += " WHERE g.staff_id = %s"
            params.append(staff_id)
        query += " ORDER BY g.generated_at DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, params)
        cols = ["id", "staff_id", "template_id", "file_path", "reference",
                "generated_at", "generated_by", "status", "template_title",
                "family", "code", "first_name", "last_name"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def update_generated_letter_status(letter_id: int, status: str) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute("UPDATE blado_generated_letter SET status = %s WHERE id = %s",
                    (status, letter_id))
        return True

    # ------------------------------------------------------------------
    # Todo / Kanban
    # ------------------------------------------------------------------

    @staticmethod
    def ensure_todo_table():
        conn = db.server_conn
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blado_todo (
                    id          SERIAL PRIMARY KEY,
                    staff_id    INT,
                    task_type   VARCHAR(32) DEFAULT 'custom',
                    description TEXT,
                    status      VARCHAR(16) DEFAULT 'todo',
                    assigned_to INT,
                    created_by  INT,
                    created_at  TIMESTAMP DEFAULT NOW(),
                    due_date    DATE,
                    resolved_at TIMESTAMP,
                    resolved_by INT,
                    log         JSONB
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_staff_todo_status ON blado_todo(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_staff_todo_assigned ON blado_todo(assigned_to)")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    @staticmethod
    def get_todos() -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, COALESCE(t.assigned_to, 0) AS staff_id, t.task_type, t.description, t.status,
                   t.assigned_to, t.created_by, t.created_at, t.due_date,
                   t.resolved_at, t.resolved_by, t.log
            FROM blado_todo t
            ORDER BY t.created_at DESC
        """)
        cols = ["id", "staff_id", "task_type", "description", "status",
                "assigned_to", "created_by", "created_at", "due_date",
                "resolved_at", "resolved_by", "log"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def create_todo(description: str, task_type: str,
                    due_date: str | None = None,
                    staff_id: int | None = None,
                    created_by: int | None = None) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO blado_todo (description, task_type, due_date, staff_id, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (description, task_type, due_date, staff_id, created_by))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False

    @staticmethod
    def move_todo(task_id: int, new_status: str, comment: str = "",
                  user_id: int = 0) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        import json
        entry = json.dumps({
            "action": new_status,
            "comment": comment,
            "user": user_id,
            "at": datetime.now().isoformat(),
        })
        try:
            cur = conn.cursor()
            if new_status == "doing":
                cur.execute(
                    """UPDATE blado_todo SET status='doing', assigned_to=%s,
                       log = COALESCE(log, '[]'::jsonb) || %s::jsonb
                       WHERE id=%s""",
                    (user_id, entry, task_id))
            elif new_status == "done":
                cur.execute(
                    """UPDATE blado_todo SET status='done', resolved_at=NOW(),
                       resolved_by=%s,
                       log = COALESCE(log, '[]'::jsonb) || %s::jsonb
                       WHERE id=%s""",
                    (user_id, entry, task_id))
            else:
                cur.execute(
                    """UPDATE blado_todo SET status='todo', assigned_to=NULL,
                       resolved_at=NULL, resolved_by=NULL,
                       log = COALESCE(log, '[]'::jsonb) || %s::jsonb
                       WHERE id=%s""",
                    (entry, task_id))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False

    @staticmethod
    def delete_todo(task_id: int) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM blado_todo WHERE id=%s", (task_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False


_FALLBACK_CATEGORIES = [
    {"key": "personal",  "label": "Fiche personnelle",  "icon": "person",      "order": 0},
    {"key": "degrees",   "label": "Diplômes & Langues", "icon": "school",      "order": 1},
    {"key": "contracts", "label": "Contrats",           "icon": "assignment",  "order": 2},
    {"key": "leave",     "label": "Congés",             "icon": "event",       "order": 3},
    {"key": "documents", "label": "Documents",          "icon": "folder",      "order": 4},
    {"key": "letters",   "label": "Courriers",          "icon": "subject",        "order": 5},
    {"key": "events",    "label": "Événements",         "icon": "history",     "order": 6},
]