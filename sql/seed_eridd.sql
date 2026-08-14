BEGIN;

INSERT INTO consultants (id, nom, sigle, forme_juridique, telephone, whatsapp, email, adresse, ville, pays, est_actif)
VALUES (1, 'ERIDD RH', 'ERIDD', 'SARL', '+228 90 00 00 01', '+228 90 00 00 01', 'contact@eridd.tg', 'BP 12345, Lome', 'Lome', 'Togo', TRUE)
ON CONFLICT (id) DO UPDATE SET nom='ERIDD RH', est_actif=TRUE;

INSERT INTO entreprises (id, nom, sigle, forme_juridique, telephone, whatsapp, email, adresse, ville, pays, is_self, est_active)
VALUES (1, 'Steel Togo', 'STEEL', 'SA', '+228 90 00 00 02', '+228 90 00 00 02', 'info@steeltogo.tg', 'Zone Industrielle du Port, BP 4567, Lome', 'Lome', 'Togo', FALSE, TRUE)
ON CONFLICT (id) DO UPDATE SET nom='Steel Togo', est_active=TRUE;

INSERT INTO missions (consultant_id, entreprise_id, reference, type_mission, titre, description,
    date_debut, montant, devise, periodicite, modalites_paiement,
    gerer_paie, gerer_contrats, gerer_conges, gerer_recrutement, gerer_discipline, gerer_documents,
    statut, delai_preavis_jours)
SELECT 1, 1, 'M2026-001', 'gestion_rh_complete', 'Externalisation RH complete - Steel Togo',
    'Gestion administrative complete du personnel, paie, declarations CNSS, contrats, discipline.',
    '2026-01-01', 500000, 'XOF', 'mensuel', 'Virement bancaire le 5 du mois',
    TRUE, TRUE, TRUE, FALSE, TRUE, TRUE,
    'active', 30
WHERE NOT EXISTS (SELECT 1 FROM missions WHERE reference = 'M2026-001');

-- Backfill multi-clients : les employés existants héritent du client de leur
-- service (idempotent — ne touche que fk_entreprise_id NULL).
UPDATE blado_employee SET fk_entreprise_id = s.entreprise_id
FROM services s
WHERE s.id = blado_employee.fk_service_id
  AND blado_employee.fk_entreprise_id IS NULL
  AND blado_employee.is_active = TRUE;

-- Colonnes ajoutées après le schéma initial (idempotent)
ALTER TABLE blado_letter_template ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
ALTER TABLE blado_letter_template ADD COLUMN IF NOT EXISTS source_code VARCHAR(8);
ALTER TABLE blado_letter_template ADD COLUMN IF NOT EXISTS created_by INTEGER;

-- Réalignement des séquences après insertion d'IDs explicites
-- (sinon nextval repart de 1 → UniqueViolation à la création suivante)
SELECT setval(pg_get_serial_sequence('consultants','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM consultants;
SELECT setval(pg_get_serial_sequence('entreprises','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM entreprises;
SELECT setval(pg_get_serial_sequence('missions','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM missions;

COMMIT;
