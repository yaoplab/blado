"""BladoDatabase — couche d'accès aux données RH centralisée."""
from __future__ import annotations

import json
from typing import Any
from datetime import date, datetime

from bladocommon.database import db


from Blado.common.blado_payroll import BladoPayrollMixin
from Blado.common.blado_hr_mixin import BladoHRMixin

class BladoDatabase(BladoPayrollMixin, BladoHRMixin):

    # ------------------------------------------------------------------
    # Staff — recherche et lecture
    # ------------------------------------------------------------------

    @staticmethod
    def get_staff_full(staff_id: int) -> dict[str, Any] | None:
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            SELECT a.id, a.first_name, a.last_name, a.email, a.phone_home,
                   a.phone_mobile, a.personal_email, a.hire_date,
                   a.is_active,
                   a.civility, a.nationality, a.marital_status, a.children_count,
                   a.emergency_contact_name, a.emergency_contact_phone,
                   a.blood_type, a.cnss_number, a.tax_id,
                   a.id_document_type, a.id_document_number, a.id_document_expiry,
                   a.matricule, a.professional_category, a.emp_status,
                   a.departure_date, a.departure_reason,
                   a.fk_service_id, a.fk_supervisor_id
            FROM blado_employee a
            WHERE a.id = %s
        """, (staff_id,))
        row = cur.fetchone()
        if not row:
            return None
        return BladoDatabase._row_to_staff(row)

    @staticmethod
    def search_staff(id_lo: int, id_hi: int, is_staff: bool = False,
                     search_text: str = "", filters: dict | None = None) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()

        # BLADO: merged table — all columns directly in a, no self-JOINs
        base_cols = """
            a.id, a.first_name, a.last_name, a.email,
            a.emp_status, a.fk_service_id,
            a.professional_category, a.matricule,
            c.label AS service_label, COALESCE(c.color, '#1565C0') AS service_color
        """
        query = f"""
            SELECT {base_cols}
            FROM blado_employee a
            LEFT JOIN services c ON a.fk_service_id = c.id
            WHERE a.is_active = TRUE
        """

        params: list[Any] = []

        ft = (search_text or "").strip().lower()
        if ft:
            query += (" AND (LOWER(a.first_name) LIKE %s OR LOWER(a.last_name) LIKE %s"
                      " OR LOWER(a.email) LIKE %s"
                      " OR LOWER(a.first_name || ' ' || a.last_name) LIKE %s"
                      " OR LOWER(a.matricule) LIKE %s)")
            like = f"%{ft}%"
            params.extend([like, like, like, like, like])

        if filters:
            if filters.get("service_id"):
                query += " AND a.fk_service_id = %s"
                params.append(filters["service_id"])
            if filters.get("status"):
                query += " AND a.emp_status = %s"
                params.append(filters["status"])

        sort = (filters or {}).get("sort", "name")
        if sort == "name":
            query += " ORDER BY a.last_name, a.first_name"
        elif sort == "seniority":
            query += " ORDER BY a.hire_date ASC"
        elif sort == "hire_date":
            query += " ORDER BY a.hire_date DESC"

        cur.execute(query, params)
        return [BladoDatabase._row_to_staff_compact(r, is_staff) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Staff — sauvegarde
    # ------------------------------------------------------------------

    @staticmethod
    def save_staff(staff_id: int, data: dict[str, Any]) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            aec_fields = [
                'first_name', 'last_name', 'email', 'phone_home', 'phone_mobile',
                'personal_email', 'hire_date',
                'civility', 'nationality', 'marital_status', 'children_count',
                'emergency_contact_name', 'emergency_contact_phone',
                'blood_type', 'cnss_number', 'tax_id',
                'id_document_type', 'id_document_number', 'id_document_expiry',
                'matricule', 'professional_category', 'emp_status',
                'departure_date', 'departure_reason', 'fk_service_id', 'fk_supervisor_id',
            ]
            sets = []
            vals: list[Any] = []
            for f in aec_fields:
                if f in data:
                    sets.append(f"{f} = %s")
                    vals.append(data[f])
            if sets:
                vals.append(staff_id)
                cur.execute(f"UPDATE blado_employee SET {', '.join(sets)} WHERE id = %s", vals)

            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def create_staff(id_lo: int, id_hi: int, data: dict[str, Any]) -> int | None:
        """Active un slot gabarit existant (UPDATE uniquement — jamais d'INSERT).

        Pattern LarcSecretaire : les lignes blado_employee sont pré-allouées.
        La création = UPDATE d'un slot avec is_active=FALSE + last_name LIKE 'Name of %'.
        """
        conn = db.server_conn
        if not conn:
            return None
        cur = conn.cursor()
        try:
            # Trouver un slot libre dans la plage
            cur.execute("""
                SELECT id FROM blado_employee
                WHERE id BETWEEN %s AND %s AND is_active = FALSE
                AND (first_name LIKE 'ID%%' OR last_name LIKE 'ID%%')
                ORDER BY id LIMIT 1
                FOR UPDATE
            """, (id_lo, id_hi))
            row = cur.fetchone()
            if not row:
                return None  # plus de slot → lancer migration_staff_gabarit.sql
            new_id = row[0]

            # BLADO: simple UPDATE — pas de rôles, pas de colonnes scolaires
            cur.execute("""
                UPDATE blado_employee SET
                    first_name = %s, last_name = %s, email = %s,
                    is_active = TRUE, emp_status = 'actif',
                    hire_date = COALESCE(%s, hire_date, NOW()),
                    updated_at = NOW()
                WHERE id = %s
            """, (data['first_name'], data['last_name'], data.get('email', ''),
                  data.get('hire_date'), new_id))

            return new_id
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------
    # Degrees
    # ------------------------------------------------------------------

    @staticmethod
    def get_degrees(staff_id: int) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute(
            "SELECT id, degree_type, institution, year_obtained, country, field_of_study "
            "FROM blado_degree WHERE staff_id = %s ORDER BY year_obtained DESC",
            (staff_id,))
        return [{"id": r[0], "degree_type": r[1], "institution": r[2],
                 "year_obtained": r[3], "country": r[4], "field_of_study": r[5]}
                for r in cur.fetchall()]

    @staticmethod
    def save_degree(staff_id: int, data: dict[str, Any]) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            if data.get("id"):
                cur.execute("""
                    UPDATE blado_degree SET degree_type=%s, institution=%s, year_obtained=%s,
                    country=%s, field_of_study=%s WHERE id=%s AND staff_id=%s
                """, (data["degree_type"], data.get("institution"), data.get("year_obtained"),
                      data.get("country"), data.get("field_of_study"), data["id"], staff_id))
            else:
                cur.execute("""
                    INSERT INTO blado_degree (staff_id, degree_type, institution, year_obtained, country, field_of_study)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (staff_id, data["degree_type"], data.get("institution"),
                      data.get("year_obtained"), data.get("country"), data.get("field_of_study")))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def delete_degree(degree_id: int, staff_id: int) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute("DELETE FROM blado_degree WHERE id = %s AND staff_id = %s", (degree_id, staff_id))
        return True

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------

    @staticmethod
    def get_languages(staff_id: int) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute(
            "SELECT id, language, proficiency FROM blado_language WHERE staff_id = %s ORDER BY language",
            (staff_id,))
        return [{"id": r[0], "language": r[1], "proficiency": r[2]} for r in cur.fetchall()]

    @staticmethod
    def save_language(staff_id: int, data: dict[str, Any]) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO blado_language (staff_id, language, proficiency)
                VALUES (%s, %s, %s)
                ON CONFLICT (staff_id, language) DO UPDATE SET proficiency = %s
            """, (staff_id, data["language"], data.get("proficiency", "B1"), data.get("proficiency", "B1")))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def delete_language(staff_id: int, language: str) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute("DELETE FROM blado_language WHERE staff_id = %s AND language = %s", (staff_id, language))
        return True

    # ------------------------------------------------------------------
    # Contracts
    # ------------------------------------------------------------------

    @staticmethod
    def get_contracts(staff_id: int) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute("""
            SELECT id, contract_type, date_debut, date_fin, periode_essai,
                   periode_essai_fin, salaire_brut, volume_horaire,
                   classification, echelon, statut, notes, created_at
            FROM blado_contract WHERE staff_id = %s ORDER BY date_debut DESC
        """, (staff_id,))
        cols = ["id", "contract_type", "date_debut", "date_fin", "periode_essai",
                "periode_essai_fin", "salaire_brut", "volume_horaire",
                "classification", "echelon", "statut", "notes", "created_at"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def save_contract(data: dict[str, Any]) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            fields = ['staff_id', 'contract_type', 'date_debut', 'date_fin',
                      'periode_essai', 'periode_essai_fin', 'salaire_brut',
                      'volume_horaire', 'classification', 'echelon', 'statut', 'notes']
            if data.get("id"):
                cur.execute(f"""
                    UPDATE blado_contract SET {', '.join(f'{f}=%s' for f in fields)}, updated_at=NOW()
                    WHERE id=%s
                """, [data.get(f) for f in fields] + [data["id"]])
            else:
                placeholders = ', '.join('%s' for _ in fields)
                cur.execute(f"""
                    INSERT INTO blado_contract ({', '.join(fields)})
                    VALUES ({placeholders})
                """, [data.get(f) for f in fields])
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    # Leave
    # ------------------------------------------------------------------

    @staticmethod
    def get_leave_balance(staff_id: int, year: int | None = None) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        if year is None:
            year = date.today().year
        cur.execute("""
            SELECT id, year, leave_type, total_days, used_days,
                   (total_days - used_days) AS remaining
            FROM blado_leave_balance WHERE staff_id = %s AND year = %s
            ORDER BY leave_type
        """, (staff_id, year))
        cols = ["id", "year", "leave_type", "total_days", "used_days", "remaining"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def ensure_annual_leave(staff_id: int, year: int | None = None) -> bool:
        """Crédite automatiquement 30 jours de congé annuel si pas encore initialisé."""
        conn = db.server_conn
        if not conn:
            return False
        if year is None:
            year = date.today().year
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO blado_leave_balance (staff_id, year, leave_type, total_days, used_days)
                VALUES (%s, %s, 'CA', 30, 0)
                ON CONFLICT (staff_id, year, leave_type) DO NOTHING
            """, (staff_id, year))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def get_leave_requests(staff_id: int | None = None,
                           status: str | None = None) -> list[dict[str, Any]]:
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        query = """
            SELECT r.id, r.staff_id, a.first_name, a.last_name, r.leave_type,
                   r.date_debut, r.date_fin, r.nb_days, r.motif, r.attachment_path,
                   r.status, r.requested_at, r.validated_by, r.validated_at, r.validation_note
            FROM blado_leave_request r
            JOIN blado_employee a ON a.id = r.staff_id
        """
        params: list[Any] = []
        conditions = []
        if staff_id is not None:
            conditions.append("r.staff_id = %s")
            params.append(staff_id)
        if status is not None:
            conditions.append("r.status = %s")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY r.requested_at DESC LIMIT 100"
        cur.execute(query, params)
        cols = ["id", "staff_id", "first_name", "last_name", "leave_type",
                "date_debut", "date_fin", "nb_days", "motif", "attachment_path",
                "status", "requested_at", "validated_by", "validated_at", "validation_note"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def save_leave_request(data: dict[str, Any]) -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO blado_leave_request
                    (staff_id, leave_type, date_debut, date_fin, nb_days, motif, attachment_path, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'en_attente')
            """, (data["staff_id"], data["leave_type"], data["date_debut"],
                  data["date_fin"], data["nb_days"], data.get("motif"),
                  data.get("attachment_path")))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def validate_leave_request(request_id: int, validated_by: int,
                               approved: bool, note: str = "") -> bool:
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            new_status = 'valide' if approved else 'refuse'
            cur.execute("""
                UPDATE blado_leave_request
                SET status = %s, validated_by = %s, validated_at = NOW(), validation_note = %s
                WHERE id = %s
            """, (new_status, validated_by, note, request_id))

            if approved:
                cur.execute("""
                    UPDATE blado_leave_balance
                    SET used_days = used_days + sub.nb_days
                    FROM (SELECT staff_id, leave_type, nb_days FROM blado_leave_request WHERE id = %s) AS sub
                    WHERE blado_leave_balance.staff_id = sub.staff_id
                    AND blado_leave_balance.leave_type = sub.leave_type
                    AND blado_leave_balance.year = EXTRACT(YEAR FROM (SELECT date_debut FROM blado_leave_request WHERE id = %s))::INTEGER
                """, (request_id, request_id))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def revoke_leave_request(request_id: int) -> bool:
        """Révoque une validation : remet en attente et annule l'impact sur le solde."""
        conn = db.server_conn
        if not conn:
            return False
        cur = conn.cursor()
        try:
            # Restore balance if it was approved
            cur.execute("""
                UPDATE blado_leave_balance
                SET used_days = used_days - sub.nb_days
                FROM (SELECT staff_id, leave_type, nb_days, status FROM blado_leave_request WHERE id = %s) AS sub
                WHERE blado_leave_balance.staff_id = sub.staff_id
                AND blado_leave_balance.leave_type = sub.leave_type
                AND blado_leave_balance.year = EXTRACT(YEAR FROM (SELECT date_debut FROM blado_leave_request WHERE id = %s))::INTEGER
                AND sub.status = 'valide'
            """, (request_id, request_id))

            # Reset to en_attente
            cur.execute("""
                UPDATE blado_leave_request
                SET status = 'en_attente', validated_by = NULL,
                    validated_at = NULL, validation_note = NULL
                WHERE id = %s AND status IN ('valide', 'refuse')
            """, (request_id,))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    # Dashboard / KPIs
    # ------------------------------------------------------------------

    @staticmethod
    def get_dashboard_kpis() -> dict[str, Any]:
        conn = db.server_conn
        if not conn:
            return {}
        cur = conn.cursor()

        def _safe_count(label: str, query: str, params=None) -> int:
            try:
                cur.execute(query, params or ())
                return cur.fetchone()[0] or 0
            except Exception:
                import traceback
                traceback.print_exc()
                return -1

        total_active = _safe_count("total_active", """
            SELECT COUNT(*) FROM (
                SELECT a.id FROM blado_employee a
                WHERE a.is_active = TRUE AND a.is_active = TRUE
                  AND a.emp_status = 'actif' AND a.departure_date IS NULL
                UNION
                SELECT a.id FROM blado_employee a
                WHERE a.is_active = TRUE AND a.is_active = TRUE
                  AND a.emp_status = 'actif' AND a.departure_date IS NULL
            ) AS staff
        """)
        active_contracts = _safe_count("active_contracts",
            "SELECT COUNT(*) FROM blado_contract WHERE statut = 'actif'")
        pending_leave = _safe_count("pending_leave",
            "SELECT COUNT(*) FROM blado_leave_request WHERE status = 'en_attente'")
        expiring = _safe_count("expiring_contracts",
            "SELECT COUNT(*) FROM blado_contract WHERE statut = 'actif'"
            " AND date_fin IS NOT NULL AND date_fin <= CURRENT_DATE + INTERVAL '30 days'")
        absent_today = _safe_count("absent_today",
            "SELECT COUNT(*) FROM blado_leave_request WHERE status = 'valide'"
            " AND CURRENT_DATE BETWEEN date_debut AND date_fin")
        return {
            "total_active": total_active,
            "active_contracts": active_contracts,
            "pending_leave": pending_leave,
            "expiring_contracts": expiring,
            "absent_today": absent_today,
        }

    @staticmethod
    def get_headcount_by_service() -> list[dict[str, Any]]:
        """Effectif actif par service (label, color, count)."""
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT c.label, COALESCE(c.color, '#1565C0'), COUNT(DISTINCT a.id)
                FROM blado_employee a
                JOIN services c ON a.fk_service_id = c.id
                WHERE a.emp_status = 'actif' AND a.departure_date IS NULL
                  AND (a.is_active = TRUE OR a.is_active = TRUE)
                GROUP BY c.id, c.label, c.color
                ORDER BY COUNT(DISTINCT a.id) DESC
            """)
            cols = ["label", "color", "count"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_contracts_by_type() -> list[dict[str, Any]]:
        """Contrats actifs groupés par type."""
        conn = db.server_conn
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT contract_type, COUNT(*) AS cnt
                FROM blado_contract WHERE statut = 'actif'
                GROUP BY contract_type ORDER BY cnt DESC
            """)
            cols = ["type", "count"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_absence_rate_30d() -> dict[str, Any]:
        """Taux d'absentéisme sur 30 jours glissants + période précédente (delta)."""
        conn = db.server_conn
        if not conn:
            return {"rate": 0, "delta": 0, "days_with_absence": 0, "total_events": 0}
        cur = conn.cursor()
        try:
            # Jours avec au moins une absence sur les 30 derniers jours
            cur.execute("""
                SELECT COUNT(DISTINCT DATE(event_at))
                FROM blado_event
                WHERE event_type LIKE 'Absence%%'
                  AND event_at >= CURRENT_DATE - INTERVAL '30 days'
                  AND event_at < CURRENT_DATE
            """)
            days_current = cur.fetchone()[0] or 0
            # Période précédente (30–60 jours)
            cur.execute("""
                SELECT COUNT(DISTINCT DATE(event_at))
                FROM blado_event
                WHERE event_type LIKE 'Absence%%'
                  AND event_at >= CURRENT_DATE - INTERVAL '60 days'
                  AND event_at < CURRENT_DATE - INTERVAL '30 days'
            """)
            days_previous = cur.fetchone()[0] or 0
            # Total events current period
            cur.execute("""
                SELECT COUNT(*) FROM blado_event
                WHERE event_type LIKE 'Absence%%'
                  AND event_at >= CURRENT_DATE - INTERVAL '30 days'
                  AND event_at < CURRENT_DATE
            """)
            total_events = cur.fetchone()[0] or 0

            rate = round(days_current / 30.0 * 100, 1) if days_current > 0 else 0.0
            prev_rate = round(days_previous / 30.0 * 100, 1) if days_previous > 0 else 0.0
            delta = round(rate - prev_rate, 1)
            return {"rate": rate, "delta": delta, "days_with_absence": days_current,
                    "total_events": total_events}
        except Exception:
            import traceback
            traceback.print_exc()
            return {"rate": 0, "delta": 0, "days_with_absence": 0, "total_events": 0}

    @staticmethod
    def get_overdue_tasks() -> int:
        """Nombre de tâches en retard (due_date passée, non terminées)."""
        conn = db.server_conn
        if not conn:
            return 0
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT COUNT(*) FROM blado_todo
                WHERE due_date IS NOT NULL AND due_date < CURRENT_DATE
                  AND status != 'done'
            """)
            return cur.fetchone()[0] or 0
        except Exception:
            import traceback
            traceback.print_exc()
            return 0

    @staticmethod
    def get_completeness_stats() -> dict[str, Any]:
        """Score de complétude : employés actifs avec tous les champs P0 remplis."""
        conn = db.server_conn
        if not conn:
            return {"total": 0, "complete": 0, "incomplete": 0, "pct": 0}
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT COUNT(*) FROM blado_employee a
                WHERE a.emp_status = 'actif' AND a.departure_date IS NULL
                  AND (a.is_active = TRUE OR a.is_active = TRUE)
            """)
            total = cur.fetchone()[0] or 0
            cur.execute("""
                SELECT COUNT(*) FROM blado_employee a
                WHERE a.emp_status = 'actif' AND a.departure_date IS NULL
                  AND (a.is_active = TRUE OR a.is_active = TRUE)
                  AND a.cnss_number IS NOT NULL AND a.cnss_number != ''
                  AND a.matricule IS NOT NULL AND a.matricule != ''
                  AND a.emergency_contact_name IS NOT NULL AND a.emergency_contact_name != ''
                  AND a.emergency_contact_phone IS NOT NULL AND a.emergency_contact_phone != ''
                  AND a.id_document_number IS NOT NULL AND a.id_document_number != ''
                  AND EXISTS (SELECT 1 FROM blado_contract c WHERE c.staff_id = a.id AND c.statut = 'actif')
            """)
            complete = cur.fetchone()[0] or 0
            incomplete = total - complete
            pct = round(complete / total * 100) if total > 0 else 0
            return {"total": total, "complete": complete, "incomplete": incomplete, "pct": pct}
        except Exception:
            import traceback
            traceback.print_exc()
            return {"total": 0, "complete": 0, "incomplete": 0, "pct": 0}

    @staticmethod
    def get_expiring_id_docs() -> int:
        """Pièces d'identité expirées ou expirant dans les 30 jours."""
        conn = db.server_conn
        if not conn:
            return 0
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT COUNT(*) FROM blado_employee
                WHERE emp_status = 'actif' AND departure_date IS NULL
                  AND id_document_expiry IS NOT NULL
                  AND id_document_expiry <= CURRENT_DATE + INTERVAL '30 days'
            """)
            return cur.fetchone()[0] or 0
        except Exception:
            import traceback
            traceback.print_exc()
            return 0
