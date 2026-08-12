-- BladoDB: schéma complet pour le logiciel RH autonome Blado
-- À exécuter sur PostgreSQL local (127.0.0.1:55515)
-- Usage: psql -h 127.0.0.1 -p 55515 -U postgres -d BladoDB -f init_blado.sql

BEGIN;

-- ============================================================================
-- 1. ENTREPRISE — profil de l'entreprise (mode RH) ou client (mode Consultant)
-- ============================================================================
CREATE TABLE IF NOT EXISTS entreprises (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(150) NOT NULL,
    sigle           VARCHAR(20),
    forme_juridique VARCHAR(50),          -- SA, SARL, EURL, SAS, freelance, etc.
    registre_commerce VARCHAR(50),
    id_fiscal       VARCHAR(50),
    -- Contact
    telephone       VARCHAR(30),
    whatsapp        VARCHAR(30),
    email           VARCHAR(100),
    site_web        VARCHAR(100),
    facebook        VARCHAR(150),
    linkedin        VARCHAR(150),
    twitter         VARCHAR(150),
    -- Adresse
    adresse         TEXT,
    code_postal     VARCHAR(10),
    ville           VARCHAR(100),
    pays            VARCHAR(50) DEFAULT 'Togo',
    -- Logo
    logo_path       VARCHAR(255),
    -- Métadonnées
    est_active      BOOLEAN DEFAULT TRUE,
    is_self         BOOLEAN DEFAULT FALSE,   -- TRUE = l'entreprise qui utilise Blado (mode RH)
    notes           TEXT,
    color           VARCHAR(20) DEFAULT '#1565C0',
    -- Audit
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 2. CONSULTANTS — profil du consultant (mode Consultant)
-- ============================================================================
CREATE TABLE IF NOT EXISTS consultants (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(150) NOT NULL,
    sigle           VARCHAR(20),
    forme_juridique VARCHAR(50),          -- freelance, EURL, SARL, etc.
    matricule_fiscal VARCHAR(50),
    -- Contact
    telephone       VARCHAR(30),
    whatsapp        VARCHAR(30),
    email           VARCHAR(100),
    site_web        VARCHAR(100),
    -- Adresse
    adresse         TEXT,
    code_postal     VARCHAR(10),
    ville           VARCHAR(100),
    pays            VARCHAR(50) DEFAULT 'Togo',
    -- Signature (pour les courriers générés)
    signature_nom       VARCHAR(150),
    signature_titre     VARCHAR(150),     -- ex: "Consultant RH Senior"
    -- Logo
    logo_path       VARCHAR(255),
    -- Métadonnées
    est_actif       BOOLEAN DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 3. SERVICES — départements/divisions (remplace larcauth_campus)
-- ============================================================================
CREATE TABLE IF NOT EXISTS services (
    id              SERIAL PRIMARY KEY,
    label           VARCHAR(100) NOT NULL,
    code            VARCHAR(16),
    description     TEXT,
    color           VARCHAR(20) DEFAULT '#64748B',
    entreprise_id   INTEGER REFERENCES entreprises(id) ON DELETE CASCADE,
    manager_id      INTEGER,                -- FK vers blado_employee (ajouté après)
    enabled         BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 4. MISSIONS — cadre contractuel consultant ↔ entreprise
-- ============================================================================
CREATE TABLE IF NOT EXISTS missions (
    id              SERIAL PRIMARY KEY,
    consultant_id   INTEGER NOT NULL REFERENCES consultants(id) ON DELETE CASCADE,
    entreprise_id   INTEGER NOT NULL REFERENCES entreprises(id) ON DELETE CASCADE,

    -- Référence contractuelle
    reference       VARCHAR(50),           -- ex: "M2026-001"
    type_mission    VARCHAR(50) NOT NULL,  -- 'gestion_rh_complete', 'paie', 'recrutement',
                                           -- 'formation', 'audit_rh', 'interim', 'autre'
    titre           VARCHAR(200),          -- ex: "Externalisation complète RH 2026"
    description     TEXT,

    -- Cadre temporel
    date_debut      DATE NOT NULL,
    date_fin        DATE,                  -- NULL = mission ouverte / tacite reconduction
    date_signature  DATE,

    -- Cadre financier
    montant         NUMERIC(12,2),
    devise          VARCHAR(3) DEFAULT 'XOF',
    periodicite     VARCHAR(20),           -- 'mensuel', 'trimestriel', 'forfait', 'unique'
    modalites_paiement TEXT,

    -- Périmètre RH couvert par cette mission
    gerer_paie          BOOLEAN DEFAULT FALSE,
    gerer_contrats      BOOLEAN DEFAULT FALSE,
    gerer_conges        BOOLEAN DEFAULT FALSE,
    gerer_recrutement   BOOLEAN DEFAULT FALSE,
    gerer_formations    BOOLEAN DEFAULT FALSE,
    gerer_discipline    BOOLEAN DEFAULT FALSE,
    gerer_documents     BOOLEAN DEFAULT FALSE,

    -- Clauses
    clause_confidentialite  TEXT,
    clause_resiliation      TEXT,
    delai_preavis_jours     INTEGER DEFAULT 30,

    -- Pièce jointe
    contrat_pdf_path        VARCHAR(255),

    -- Statut
    statut          VARCHAR(20) DEFAULT 'active',  -- brouillon, active, suspendue, terminee, resiliee
    notes           TEXT,
    nb_employes_geres   INTEGER DEFAULT 0,

    -- Audit
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER,
    updated_by      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_missions_consultant ON missions(consultant_id);
CREATE INDEX IF NOT EXISTS idx_missions_entreprise ON missions(entreprise_id);
CREATE INDEX IF NOT EXISTS idx_missions_statut ON missions(statut);

-- ============================================================================
-- 5. BLADO_EMPLOYEE — fiche employé (fusion larcauth_aecuser + larcauth_staff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_employee (
    id              SERIAL PRIMARY KEY,
    fk_service_id   INTEGER REFERENCES services(id) ON DELETE SET NULL,
    fk_entreprise_id INTEGER REFERENCES entreprises(id) ON DELETE SET NULL,
    fk_supervisor_id INTEGER REFERENCES blado_employee(id) ON DELETE SET NULL,

    -- Identité
    civility        VARCHAR(8),            -- M., Mme, Dr, Pr
    first_name      VARCHAR(80) NOT NULL,
    last_name       VARCHAR(80) NOT NULL,
    email           VARCHAR(150),
    phone_mobile    VARCHAR(20),
    phone_home      VARCHAR(20),
    personal_email  VARCHAR(150),

    -- Photo
    photo_path      TEXT,

    -- Professionnel
    matricule       VARCHAR(30),
    professional_category VARCHAR(30),
    hire_date       DATE,
    departure_date  DATE,
    departure_reason TEXT,
    emp_status      VARCHAR(20) DEFAULT 'actif',  -- actif, suspendu, en_preavis, parti

    -- Rôles RH (ex larcauth_staff booleans)
    type_DRH                    BOOLEAN DEFAULT FALSE,
    type_Comptable              BOOLEAN DEFAULT FALSE,
    type_ressources_Humaines    BOOLEAN DEFAULT FALSE,
    type_Bulletin_Releves       BOOLEAN DEFAULT FALSE,
    type_Manager                BOOLEAN DEFAULT FALSE,
    type_Administrateur         BOOLEAN DEFAULT FALSE,

    -- RH
    nationality     VARCHAR(72),
    marital_status  VARCHAR(20),
    children_count  INT DEFAULT 0,
    emergency_contact_name   VARCHAR(150),
    emergency_contact_phone  VARCHAR(20),
    blood_type      VARCHAR(4),
    cnss_number     VARCHAR(30),
    tax_id          VARCHAR(30),
    id_document_type        VARCHAR(30),
    id_document_number      VARCHAR(50),
    id_document_expiry      DATE,

    -- Statut
    is_active       BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 6. BLADO_USER — comptes de connexion
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_user (
    id              SERIAL PRIMARY KEY,
    employee_id     INTEGER REFERENCES blado_employee(id) ON DELETE SET NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password        VARCHAR(64) NOT NULL,    -- SHA-256 hex
    full_name       VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'ADMIN',  -- ADMIN, RH, MANAGER, CONSULTANT
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 7. BLADO_EVENT — événements employé (absences, retards, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_event (
    event_id        SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    event_type      TEXT,                  -- "Absence — maladie", "Retard — transport", etc.
    event_at        TIMESTAMP,
    note            TEXT,
    source          TEXT,                  -- 'RH', 'manager', 'consultant'
    created_by      INTEGER REFERENCES blado_employee(id),
    validated_by    INTEGER REFERENCES blado_employee(id),
    created_at      TIMESTAMP DEFAULT NOW(),
    lieu_label      TEXT,
    subject_label   TEXT,
    fk_service_id   INTEGER REFERENCES services(id) ON DELETE SET NULL
);

-- ============================================================================
-- 8. BLADO_CONTRACT — contrats de travail
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_contract (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    contract_type   VARCHAR(50),           -- CDI, CDD, stage, prestation, etc.
    date_debut      DATE,
    date_fin        DATE,
    periode_essai   INTEGER,               -- durée en jours
    periode_essai_fin DATE,
    salaire_brut    NUMERIC(12,2),
    devise          VARCHAR(3) DEFAULT 'XOF',
    volume_horaire  NUMERIC(5,1),          -- heures/semaine
    classification  VARCHAR(50),
    echelon         VARCHAR(50),
    statut          VARCHAR(20) DEFAULT 'actif',  -- actif, rompu
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 9. BLADO_LEAVE — congés (solde + demandes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_leave_balance (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    year            INTEGER NOT NULL,
    leave_type      VARCHAR(30) NOT NULL DEFAULT 'CA',  -- CA (congé annuel), maladie, maternité, etc.
    total_days      NUMERIC(5,1) DEFAULT 30,
    used_days       NUMERIC(5,1) DEFAULT 0,
    UNIQUE(staff_id, year, leave_type)
);

CREATE TABLE IF NOT EXISTS blado_leave_request (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    leave_type      VARCHAR(30) NOT NULL DEFAULT 'CA',
    date_debut      DATE NOT NULL,
    date_fin        DATE NOT NULL,
    nb_days         NUMERIC(5,1),
    motif           TEXT,
    status          VARCHAR(20) DEFAULT 'en_attente',  -- en_attente, valide, refuse
    validated_by    INTEGER REFERENCES blado_employee(id),
    validated_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 10. BLADO_DEGREE & BLADO_LANGUAGE — diplômes et langues
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_degree (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    title           VARCHAR(200),
    institution     VARCHAR(200),
    year_obtained   INTEGER,
    field_of_study  VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS blado_language (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    language        VARCHAR(80),
    niveau           VARCHAR(20)  -- maternelle, courant, intermediaire, debutant
);

-- ============================================================================
-- 11. BLADO_DETAIL_CATEGORY — catégories d'onglets dans la fiche employé
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_detail_category (
    id              SERIAL PRIMARY KEY,
    category_key    VARCHAR(50) UNIQUE NOT NULL,
    label_fr        VARCHAR(100),
    label_en        VARCHAR(100),
    icon_name       VARCHAR(50),
    sort_order      INTEGER DEFAULT 0,
    enabled         BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- 12. BLADO_DOCUMENT — métadonnées des documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_document (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    category_key    VARCHAR(50),
    file_name       VARCHAR(255),
    file_path       TEXT,
    file_size       BIGINT,
    uploaded_at     TIMESTAMP DEFAULT NOW(),
    uploaded_by     INTEGER REFERENCES blado_employee(id),
    UNIQUE(staff_id, category_key, file_name)
);

-- ============================================================================
-- 13. BLADO_LETTER — templates et courriers générés
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_letter_template (
    id              SERIAL PRIMARY KEY,
    family          CHAR(1),               -- A–J
    code            VARCHAR(8),
    title           VARCHAR(200),
    description     TEXT,
    body_text       TEXT,
    docx_data       BYTEA,
    variables       TEXT[],                -- [Nom], [Matricule], [Poste], etc.
    version         INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    is_builtin      BOOLEAN DEFAULT TRUE,  -- TRUE = fourni, FALSE = personnalisé
    fk_entreprise_id INTEGER REFERENCES entreprises(id) ON DELETE CASCADE,  -- NULL = global
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blado_generated_letter (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES blado_employee(id) ON DELETE CASCADE,
    template_id     INTEGER REFERENCES blado_letter_template(id) ON DELETE SET NULL,
    file_path       TEXT,
    reference       VARCHAR(50),           -- ex: "RH/2026/0142"
    status          VARCHAR(20) DEFAULT 'draft',  -- draft, sent, archived
    created_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES blado_employee(id)
);

-- ============================================================================
-- 14. BLADO_TODO — kanban de tâches RH
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_todo (
    id              SERIAL PRIMARY KEY,
    task_type       VARCHAR(50),
    title           VARCHAR(200),
    description     TEXT,
    status          VARCHAR(20) DEFAULT 'todo',  -- todo, doing, done
    assigned_to     INTEGER REFERENCES blado_employee(id),
    due_date        DATE,
    resolved_at     TIMESTAMP,
    resolved_by     INTEGER REFERENCES blado_employee(id),
    log             JSONB DEFAULT '[]',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 15. BLADO_CONFIG — configuration clé/valeur (AppConfig)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_config (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT,
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 16. BLADO_PROFESSIONAL_CATEGORY — catégories professionnelles
-- ============================================================================
CREATE TABLE IF NOT EXISTS blado_professional_category (
    id              SERIAL PRIMARY KEY,
    label_fr        VARCHAR(100),
    label_en        VARCHAR(100),
    enabled         BOOLEAN DEFAULT TRUE,
    is_education    BOOLEAN DEFAULT FALSE
);

COMMIT;
