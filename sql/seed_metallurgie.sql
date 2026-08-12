-- BladoDB: 20 services + 99 employes par service, tous desactives
-- Pattern LarcRH: UPDATE uniquement, jamais INSERT apres seed

BEGIN;

DELETE FROM services;
DELETE FROM blado_employee;

-- 20 services, TOUS avec enabled=FALSE
INSERT INTO services (id, label, code, description, color, sort_order, enabled) VALUES
    (1,  'Service 01', 'S01', '', 'white', 0, FALSE),
    (2,  'Service 02', 'S02', '', 'white', 1, FALSE),
    (3,  'Service 03', 'S03', '', 'white', 2, FALSE),
    (4,  'Service 04', 'S04', '', 'white', 3, FALSE),
    (5,  'Service 05', 'S05', '', 'white', 4, FALSE),
    (6,  'Service 06', 'S06', '', 'white', 5, FALSE),
    (7,  'Service 07', 'S07', '', 'white', 6, FALSE),
    (8,  'Service 08', 'S08', '', 'white', 7, FALSE),
    (9,  'Service 09', 'S09', '', 'white', 8, FALSE),
    (10, 'Service 10', 'S10', '', 'white', 9, FALSE),
    (11, 'Service 11', 'S11', '', 'white', 10, FALSE),
    (12, 'Service 12', 'S12', '', 'white', 11, FALSE),
    (13, 'Service 13', 'S13', '', 'white', 12, FALSE),
    (14, 'Service 14', 'S14', '', 'white', 13, FALSE),
    (15, 'Service 15', 'S15', '', 'white', 14, FALSE),
    (16, 'Service 16', 'S16', '', 'white', 15, FALSE),
    (17, 'Service 17', 'S17', '', 'white', 16, FALSE),
    (18, 'Service 18', 'S18', '', 'white', 17, FALSE),
    (19, 'Service 19', 'S19', '', 'white', 18, FALSE),
    (20, 'Service 20', 'S20', '', 'white', 19, FALSE);

-- 99 employes inactifs par service (ID = service*100 + 1..99)
DO $$
DECLARE
    svc RECORD;
BEGIN
    FOR svc IN SELECT id FROM services ORDER BY id LOOP
        INSERT INTO blado_employee (id, fk_service_id, first_name, last_name,
            is_active, emp_status)
        SELECT svc.id * 100 + s, svc.id,
               'Employe', 'Slot ' || LPAD((svc.id*100+s)::TEXT, 5, '0'),
               FALSE, 'inactif'
        FROM generate_series(1, 99) AS s
        WHERE NOT EXISTS (SELECT 1 FROM blado_employee WHERE id = svc.id * 100 + s);
    END LOOP;
END $$;

-- Categories pro (metallurgie)
DELETE FROM blado_professional_category;
INSERT INTO blado_professional_category (label_fr, label_en, enabled) VALUES
    ('Directeur General',              'CEO',                              TRUE),
    ('Directeur de Production',        'Production Director',              TRUE),
    ('Directeur RH',                   'HR Director',                      TRUE),
    ('Ingenieur Metallurgiste',        'Metallurgical Engineer',           TRUE),
    ('Ingenieur Qualite',              'Quality Engineer',                 TRUE),
    ('Ingenieur Maintenance',          'Maintenance Engineer',             TRUE),
    ('Chef d''Equipe Fonderie',        'Foundry Team Leader',              TRUE),
    ('Chef d''Equipe Usinage',         'Machining Team Leader',            TRUE),
    ('Technicien de Production',       'Production Technician',            TRUE),
    ('Technicien Qualite',             'Quality Technician',               TRUE),
    ('Technicien Maintenance',         'Maintenance Technician',           TRUE),
    ('Operateur de Fonderie',          'Foundry Operator',                 TRUE),
    ('Soudeur / Chaudronnier',         'Welder / Boilermaker',             TRUE),
    ('Conducteur d''Engins',           'Heavy Equipment Operator',         TRUE),
    ('Controleur Qualite',             'Quality Controller',               TRUE),
    ('Agent de Maintenance',           'Maintenance Agent',                TRUE),
    ('Magasinier',                     'Storekeeper',                      TRUE),
    ('Agent HSE',                      'HSE Agent',                        TRUE),
    ('Responsable RH',                 'HR Manager',                       TRUE),
    ('Comptable',                      'Accountant',                       TRUE),
    ('Assistant Administratif',        'Administrative Assistant',         TRUE),
    ('Commercial',                     'Sales Representative',             TRUE),
    ('Chauffeur',                      'Driver',                           TRUE),
    ('Agent de Securite',              'Security Guard',                   TRUE),
    ('Agent d''Entretien',             'Maintenance Worker',               TRUE),
    ('Stagiaire',                      'Intern',                           TRUE);

COMMIT;
