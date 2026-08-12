-- BladoDB: données initiales (seed)
-- Exécuter après init_blado.sql

BEGIN;

-- Catégories de détail (onglets fiche employé)
INSERT INTO blado_detail_category (category_key, label_fr, label_en, icon_name, sort_order, enabled) VALUES
    ('personal',    'Identité',     'Identity',     'person',       0, TRUE),
    ('degrees',     'Diplômes',     'Degrees',      'school',       1, TRUE),
    ('contracts',   'Contrats',     'Contracts',     'contract',     2, TRUE),
    ('leave',       'Congés',       'Leave',        'event',        3, TRUE),
    ('documents',   'Documents',    'Documents',    'description',  4, TRUE),
    ('events',      'Événements',   'Events',       'timeline',     5, TRUE),
    ('letters',     'Courriers',    'Letters',      'receipt_long', 6, TRUE)
ON CONFLICT (category_key) DO NOTHING;

-- Catégories professionnelles par défaut
INSERT INTO blado_professional_category (label_fr, label_en, enabled, is_education) VALUES
    ('Directeur Général',       'CEO',                  TRUE, FALSE),
    ('Directeur RH',            'HR Director',          TRUE, FALSE),
    ('Responsable RH',          'HR Manager',           TRUE, FALSE),
    ('Assistant RH',            'HR Assistant',         TRUE, FALSE),
    ('Comptable',               'Accountant',           TRUE, FALSE),
    ('Responsable Paie',        'Payroll Manager',      TRUE, FALSE),
    ('Manager',                 'Manager',              TRUE, FALSE),
    ('Chef de Projet',          'Project Manager',      TRUE, FALSE),
    ('Commercial',              'Sales',                TRUE, FALSE),
    ('Assistant Administratif', 'Admin Assistant',      TRUE, FALSE),
    ('Stagiaire',               'Intern',               TRUE, FALSE),
    ('Consultant',              'Consultant',           TRUE, FALSE),
    ('Informaticien',           'IT Specialist',        TRUE, FALSE),
    ('Comptable',               'Accountant',           TRUE, FALSE),
    ('Secrétaire',              'Secretary',            TRUE, FALSE),
    ('Chauffeur',               'Driver',               TRUE, FALSE),
    ('Agent de sécurité',       'Security Guard',       TRUE, FALSE),
    ('Agent d''entretien',      'Maintenance Agent',    TRUE, FALSE)
ON CONFLICT DO NOTHING;

-- Services par défaut (utilisés si aucun n'est créé)
INSERT INTO services (label, code, description, color, sort_order) VALUES
    ('Direction',       'DIR',  'Direction générale',           '#1565C0', 0),
    ('Ressources Humaines', 'RH', 'Gestion du personnel',      '#2E7D32', 1),
    ('Comptabilité',    'CPT',  'Finances et paie',            '#E65100', 2),
    ('Informatique',    'IT',   'Services informatiques',      '#6A1B9A', 3),
    ('Commercial',      'COM',  'Ventes et marketing',         '#C62828', 4),
    ('Administratif',   'ADM',  'Secrétariat et administration', '#37474F', 5);

COMMIT;
