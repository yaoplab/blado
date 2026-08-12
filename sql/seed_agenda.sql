-- BladoDB: Calendrier 2024-2030 avec jours fériés Togo
-- Génère une ligne par jour, marque les week-ends et jours fériés

BEGIN;

CREATE TABLE IF NOT EXISTS blado_agenda (
    id              INTEGER PRIMARY KEY,
    date_all        DATE NOT NULL UNIQUE,
    j               SMALLINT DEFAULT 0,
    m               SMALLINT DEFAULT 0,
    w               SMALLINT DEFAULT 0,
    year            SMALLINT DEFAULT 0,
    year_week       SMALLINT DEFAULT 0,
    trimester       SMALLINT DEFAULT 0,
    working_day     BOOLEAN DEFAULT TRUE,
    week_day        SMALLINT DEFAULT 0,
    holiday_name    VARCHAR(100),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Génération des jours pour 2024-2030
INSERT INTO blado_agenda (id, date_all, j, m, w, year, year_week, trimester, working_day, week_day)
SELECT
    to_char(d, 'YYYYMMDD')::INTEGER AS id,
    d::DATE AS date_all,
    EXTRACT(DAY FROM d)::SMALLINT AS j,
    EXTRACT(MONTH FROM d)::SMALLINT AS m,
    ((EXTRACT(DAY FROM d)::INT - 1) / 7 + 1)::SMALLINT AS w,
    EXTRACT(YEAR FROM d)::SMALLINT AS year,
    EXTRACT(WEEK FROM d)::SMALLINT AS year_week,
    CASE WHEN EXTRACT(MONTH FROM d) <= 3 THEN 1
         WHEN EXTRACT(MONTH FROM d) <= 6 THEN 2
         WHEN EXTRACT(MONTH FROM d) <= 9 THEN 3
         ELSE 4 END::SMALLINT AS trimester,
    -- Samedi (6) et Dimanche (0) = non ouvrés
    EXTRACT(DOW FROM d) NOT IN (0, 6) AS working_day,
    EXTRACT(DOW FROM d)::SMALLINT AS week_day
FROM generate_series('2024-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
WHERE NOT EXISTS (SELECT 1 FROM blado_agenda WHERE date_all = d::DATE);

-- Jours fériés Togo (fixes + variables)
-- Fêtes fixes
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Jour de l''An'                 WHERE date_all IN ('2024-01-01','2025-01-01','2026-01-01','2027-01-01','2028-01-01','2029-01-01','2030-01-01');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Fête de l''Indépendance'      WHERE date_all IN ('2024-04-27','2025-04-27','2026-04-27','2027-04-27','2028-04-27','2029-04-27','2030-04-27');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Fête du Travail'              WHERE date_all IN ('2024-05-01','2025-05-01','2026-05-01','2027-05-01','2028-05-01','2029-05-01','2030-05-01');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Jour des Martyrs'             WHERE date_all IN ('2024-06-21','2025-06-21','2026-06-21','2027-06-21','2028-06-21','2029-06-21','2030-06-21');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Assomption'                   WHERE date_all IN ('2024-08-15','2025-08-15','2026-08-15','2027-08-15','2028-08-15','2029-08-15','2030-08-15');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Toussaint'                    WHERE date_all IN ('2024-11-01','2025-11-01','2026-11-01','2027-11-01','2028-11-01','2029-11-01','2030-11-01');
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Noël'                         WHERE date_all IN ('2024-12-25','2025-12-25','2026-12-25','2027-12-25','2028-12-25','2029-12-25','2030-12-25');

-- Pâques (dimanche — déjà non ouvré) + Lundi de Pâques (férié)
-- 2024: 31 mars (Pâques), 1er avril (Lundi)
-- 2025: 20 avril, 21 avril
-- 2026: 5 avril, 6 avril
-- 2027: 28 mars, 29 mars
-- 2028: 16 avril, 17 avril
-- 2029: 1er avril, 2 avril
-- 2030: 21 avril, 22 avril
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Lundi de Pâques' WHERE date_all IN ('2024-04-01','2025-04-21','2026-04-06','2027-03-29','2028-04-17','2029-04-02','2030-04-22');

-- Ascension (jeudi, 40j après Pâques)
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Ascension' WHERE date_all IN ('2024-05-09','2025-05-29','2026-05-14','2027-05-06','2028-05-25','2029-05-10','2030-05-30');

-- Lundi de Pentecôte (50j après Pâques)
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Lundi de Pentecôte' WHERE date_all IN ('2024-05-20','2025-06-09','2026-05-25','2027-05-17','2028-06-05','2029-05-21','2030-06-10');

-- Aïd el-Fitr (fin du Ramadan — dates approximatives, à ajuster selon observation lunaire)
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Aïd el-Fitr' WHERE date_all IN ('2024-04-10','2025-03-31','2026-03-20','2027-03-10','2028-02-28','2029-02-16','2030-02-05');

-- Aïd el-Kebir (Tabaski — dates approximatives)
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Aïd el-Kebir (Tabaski)' WHERE date_all IN ('2024-06-17','2025-06-07','2026-05-27','2027-05-17','2028-05-05','2029-04-24','2030-04-13');

-- Maouloud (naissance du Prophète — dates approximatives)
UPDATE blado_agenda SET working_day = FALSE, holiday_name = 'Maouloud' WHERE date_all IN ('2024-09-16','2025-09-05','2026-08-26','2027-08-15','2028-08-04','2029-07-25','2030-07-14');

COMMIT;
