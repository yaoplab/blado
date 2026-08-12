# BladoPayrollMixin — méthodes de paie extraites de BladoDatabase
# BLADO: fichier ≤ 1000 lignes (règle pyside6-wrapper)

from __future__ import annotations
from typing import Any
from datetime import date
from bladocommon.database import db

class BladoPayrollMixin:
    # ========================================================================
    # PAIE — Payroll (CNSS Togo, bulletins, journal)
    # ========================================================================

    @staticmethod
    def get_payroll_config() -> dict[str, float]:
        """Retourne la config paie sous forme de dict {key: value}."""
        conn = db.server_conn
        if not conn:
            return {}
        try:
            cur = conn.cursor()
            cur.execute("SELECT config_key, config_value FROM blado_payroll_config ORDER BY config_key")
            return {row[0]: float(row[1]) for row in cur.fetchall()}
        except Exception:
            return {}

    @staticmethod
    def save_payroll_config(key: str, value: float) -> bool:
        """Met à jour une valeur de config paie."""
        conn = db.server_conn
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO blado_payroll_config (config_key, config_value) VALUES (%s, %s) "
                "ON CONFLICT (config_key) DO UPDATE SET config_value = %s, updated_at = NOW()",
                (key, value, value)
            )
            return True
        except Exception:
            return False

    @staticmethod
    def generate_payslip(employee_id: int, month: int, year: int) -> dict | None:
        """
        Génère un bulletin de paie pour un employé.
        Logique Togo : brut → CNSS 4% → base imposable → net.
        """
        conn = db.server_conn
        if not conn:
            return None

        cfg = BladoDatabase.get_payroll_config()
        cnss_pct = cfg.get('cnss_employe', 4.0) / 100.0

        # 1. Salaire de base depuis le contrat actif
        cur = conn.cursor()
        cur.execute("""
            SELECT salaire_brut FROM blado_contract
            WHERE staff_id = %s AND statut = 'actif'
            ORDER BY date_debut DESC LIMIT 1
        """, (employee_id,))
        row = cur.fetchone()
        if not row:
            return None
        salaire_base = float(row[0])

        # 2. Construction des lignes
        lines = []
        brut_total = salaire_base
        lines.append({'type': 'gain', 'label': 'Salaire de base', 'montant': salaire_base, 'order': 0})

        # 3. Heures sup (si enregistrées dans blado_event ce mois-ci)
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(
                EXTRACT(EPOCH FROM (event_at)) / 3600.0
            ), 0) FROM blado_event
            WHERE staff_id = %s AND event_type LIKE 'Heure sup%%'
            AND EXTRACT(MONTH FROM event_at) = %s
            AND EXTRACT(YEAR FROM event_at) = %s
        """, (employee_id, month, year))
        hs_row = cur.fetchone()
        if hs_row and hs_row[0] > 0:
            taux_horaire = salaire_base / 173.33  # 40h/sem × 52/12
            hs_montant = round(float(hs_row[1]) * taux_horaire)
            lines.append({'type': 'gain', 'label': 'Heures supplémentaires', 'montant': hs_montant, 'order': 1})
            brut_total += hs_montant

        # 4. Primes (somme des événements "Prime" du mois)
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM blado_event
            WHERE staff_id = %s AND event_type = 'Prime'
            AND EXTRACT(MONTH FROM event_at) = %s
            AND EXTRACT(YEAR FROM event_at) = %s
        """, (employee_id, month, year))
        prime_row = cur.fetchone()
        primes = float(prime_row[0]) if prime_row else 0
        if primes > 0:
            lines.append({'type': 'gain', 'label': 'Primes', 'montant': primes, 'order': 2})
            brut_total += primes

        # 5. CNSS employé
        plafond_cnss = cfg.get('cnss_plafond', 300000)
        base_cnss = min(brut_total, plafond_cnss)
        cnss_montant = round(base_cnss * cnss_pct)
        lines.append({'type': 'deduction', 'label': 'CNSS (4%)', 'montant': cnss_montant, 'order': 100})

        # 6. Retenues (avances, saisies)
        cur.execute("""
            SELECT event_type, amount FROM blado_event
            WHERE staff_id = %s AND event_type IN ('Avance', 'Saisie')
            AND EXTRACT(MONTH FROM event_at) = %s
            AND EXTRACT(YEAR FROM event_at) = %s
        """, (employee_id, month, year))
        total_retenues = 0
        order_idx = 101
        for ev_row in cur.fetchall():
            montant_ret = float(ev_row[1]) if ev_row[1] else 0
            if montant_ret > 0:
                lines.append({'type': 'deduction', 'label': ev_row[0], 'montant': montant_ret, 'order': order_idx})
                total_retenues += montant_ret
                order_idx += 1

        # 7. Impôt (simplifié — forfait 2% sur base imposable > SMIC)
        smic = cfg.get('smic_mensuel', 35000)
        base_imposable = brut_total - cnss_montant
        impots = 0
        if base_imposable > smic:
            impots = round(base_imposable * 0.02)
            lines.append({'type': 'deduction', 'label': 'Impôt (2%)', 'montant': impots, 'order': 200})

        # 8. Net à payer
        net = brut_total - cnss_montant - total_retenues - impots
        total_primes = primes
        total_hsup = hs_montant if hs_row and hs_row[0] > 0 else 0
        total_retenues_all = cnss_montant + total_retenues + impots

        # Sauvegarder le bulletin
        try:
            cur.execute("""
                INSERT INTO blado_payslip (employee_id, period_month, period_year,
                    salaire_brut, total_primes, total_heures_sup, total_retenues,
                    cnss_employe, impots, net_a_payer, statut)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'brouillon')
                ON CONFLICT (employee_id, period_month, period_year)
                DO UPDATE SET salaire_brut = %s, total_primes = %s, total_heures_sup = %s,
                    total_retenues = %s, cnss_employe = %s, impots = %s,
                    net_a_payer = %s, statut = 'brouillon'
                RETURNING id
            """, (employee_id, month, year, brut_total, total_primes, total_hsup,
                  total_retenues_all, cnss_montant, impots, net,
                  brut_total, total_primes, total_hsup, total_retenues_all,
                  cnss_montant, impots, net))
            payslip_id = cur.fetchone()[0]

            # Supprimer les anciennes lignes et recréer
            cur.execute("DELETE FROM blado_payslip_line WHERE payslip_id = %s", (payslip_id,))
            for i, line in enumerate(lines):
                cur.execute(
                    "INSERT INTO blado_payslip_line (payslip_id, line_type, label, montant, sort_order) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (payslip_id, line['type'], line['label'], line['montant'], i)
                )
            return {
                'id': payslip_id, 'employee_id': employee_id,
                'month': month, 'year': year,
                'salaire_brut': brut_total, 'total_primes': total_primes,
                'total_heures_sup': total_hsup, 'total_retenues': total_retenues_all,
                'cnss_employe': cnss_montant, 'impots': impots,
                'net_a_payer': net, 'lines': lines,
            }
        except Exception:
            return None

    @staticmethod
    def get_payslips(month: int, year: int, entreprise_id: int | None = None) -> list[dict]:
        """Liste des bulletins pour un mois donné, avec totaux."""
        conn = db.server_conn
        if not conn:
            return []
        try:
            cur = conn.cursor()
            query = """
                SELECT p.id, p.employee_id, e.first_name, e.last_name, e.matricule,
                       s.label AS service_label, p.salaire_brut, p.total_primes,
                       p.total_heures_sup, p.total_retenues, p.cnss_employe,
                       p.impots, p.net_a_payer, p.statut
                FROM blado_payslip p
                JOIN blado_employee e ON e.id = p.employee_id
                LEFT JOIN services s ON s.id = e.fk_service_id
                WHERE p.period_month = %s AND p.period_year = %s
            """
            params = [month, year]
            if entreprise_id:
                query += " AND e.fk_entreprise_id = %s"
                params.append(entreprise_id)
            query += " ORDER BY e.last_name, e.first_name"
            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception:
            return []

    @staticmethod
    def get_payslip(payslip_id: int) -> dict | None:
        """Détail complet d'un bulletin avec ses lignes."""
        conn = db.server_conn
        if not conn:
            return None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.*, e.first_name, e.last_name, e.matricule,
                       s.label AS service_label
                FROM blado_payslip p
                JOIN blado_employee e ON e.id = p.employee_id
                LEFT JOIN services s ON s.id = e.fk_service_id
                WHERE p.id = %s
            """, (payslip_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            payslip = dict(zip(cols, row))
            cur.execute("""
                SELECT line_type, label, montant FROM blado_payslip_line
                WHERE payslip_id = %s ORDER BY sort_order
            """, (payslip_id,))
            payslip['lines'] = [dict(zip(['type', 'label', 'montant'], r)) for r in cur.fetchall()]
            return payslip
        except Exception:
            return None

    @staticmethod
    def get_payroll_journal(month: int, year: int, entreprise_id: int | None = None) -> dict:
        """Journal de paie : totaux par colonne pour le mois."""
        conn = db.server_conn
        if not conn:
            return {}
        try:
            cur = conn.cursor()
            query = """
                SELECT COUNT(*) AS nb_bulletins,
                       COALESCE(SUM(p.salaire_brut), 0) AS total_brut,
                       COALESCE(SUM(p.total_primes), 0) AS total_primes,
                       COALESCE(SUM(p.total_heures_sup), 0) AS total_heures_sup,
                       COALESCE(SUM(p.cnss_employe), 0) AS total_cnss,
                       COALESCE(SUM(p.impots), 0) AS total_impots,
                       COALESCE(SUM(p.total_retenues), 0) AS total_retenues,
                       COALESCE(SUM(p.net_a_payer), 0) AS total_net
                FROM blado_payslip p
                JOIN blado_employee e ON e.id = p.employee_id
                WHERE p.period_month = %s AND p.period_year = %s
            """
            params = [month, year]
            if entreprise_id:
                query += " AND e.fk_entreprise_id = %s"
                params.append(entreprise_id)
            cur.execute(query, params)
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            journal = dict(zip(cols, row))
            # CNSS employeur
            journal['total_cnss_employeur'] = round(journal['total_brut'] * 0.165)
            # Charges totales
            journal['total_charges'] = journal['total_cnss'] + journal['total_cnss_employeur'] + journal['total_impots']
            return journal
        except Exception:
            return {}

    @staticmethod
    def validate_payslip(payslip_id: int) -> bool:
        """Valide un bulletin (brouillon → valide)."""
        conn = db.server_conn
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("UPDATE blado_payslip SET statut = 'valide' WHERE id = %s", (payslip_id,))
            return True
        except Exception:
            return False

    @staticmethod
    def run_monthly_payroll(month: int, year: int, entreprise_id: int | None = None) -> int:
        """
        Lance la paie pour tous les employés actifs.
        Retourne le nombre de bulletins générés.
        """
        conn = db.server_conn
        if not conn:
            return 0
        count = 0
        try:
            cur = conn.cursor()
            query = """
                SELECT id FROM blado_employee WHERE is_active = TRUE AND emp_status = 'actif'
            """
            if entreprise_id:
                query += " AND fk_entreprise_id = %s"
                cur.execute(query, (entreprise_id,))
            else:
                cur.execute(query)
            for row in cur.fetchall():
                if BladoDatabase.generate_payslip(row[0], month, year):
                    count += 1
            return count
        except Exception:
            return count
