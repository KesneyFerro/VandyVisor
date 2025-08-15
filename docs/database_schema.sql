-- VandyVisor Database Schema
-- Description: PostgreSQL schema for course planning and degree audit system
-- Last Updated: August 14, 2025

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- For text search

-- ===============================
-- CATALOG DATA (read-mostly facts)
-- ===============================

-- Subjects (e.g., MATH, CS, CHEM)
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(255),
    school VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Terms (academic terms like FA2025, SP2026)
CREATE TABLE terms (
    id SERIAL PRIMARY KEY,
    term_code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    registration_start DATE,
    registration_end DATE,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Courses (master list of all courses)
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(10) NOT NULL REFERENCES subjects(subject_code),
    catalog_number VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    level INTEGER, -- e.g., 1000, 2000, 3000, 4000
    units_earned NUMERIC(3,1) NOT NULL,
    credit_hours_min INTEGER,
    credit_hours_max INTEGER,
    is_offered_fall BOOLEAN DEFAULT FALSE,
    is_offered_spring BOOLEAN DEFAULT FALSE,
    is_offered_summer BOOLEAN DEFAULT FALSE,
    terms_offered_raw TEXT, -- Original text before parsing
    prerequisites_raw TEXT, -- Original text before parsing
    corequisites_raw TEXT, -- Original text before parsing
    antirequisites_raw TEXT, -- Original text before parsing
    UNIQUE(subject_code, catalog_number),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Course Offerings (sections available in specific terms)
CREATE TABLE course_offerings (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    term_code VARCHAR(10) NOT NULL REFERENCES terms(term_code),
    class_number INTEGER NOT NULL, -- Registration system identifier
    section_number VARCHAR(10) NOT NULL,
    component VARCHAR(50), -- LEC, LAB, DIS, etc.
    instructor TEXT,
    location TEXT,
    days_of_week VARCHAR(10), -- e.g., "MWF", "TR"
    start_time TIME,
    end_time TIME,
    seats_total INTEGER,
    seats_available INTEGER,
    waitlist_count INTEGER DEFAULT 0,
    meta JSONB, -- Additional data like room, modality, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(term_code, class_number)
);

-- Attributes (tags like AXLE categories - HCA, INT, US, writing W)
CREATE TABLE attributes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    attribute_type VARCHAR(50), -- e.g., "AXLE", "WRITING", "HONORS"
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Course Attributes (which attributes apply to which courses)
CREATE TABLE course_attributes (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    attribute_id INTEGER NOT NULL REFERENCES attributes(id),
    term_code VARCHAR(10) REFERENCES terms(term_code), -- Optional, for term-specific attributes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(course_id, attribute_id, term_code)
);

-- Requisite Groups (OR layer of requisites)
CREATE TABLE requisite_groups (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    kind VARCHAR(10) NOT NULL CHECK (kind IN ('pre', 'co', 'anti')),
    logic VARCHAR(20) NOT NULL DEFAULT 'all' CHECK (logic IN ('all', 'min_count')),
    min_count INTEGER, -- Only used when logic = 'min_count'
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Requisite Group Members (AND layer of requisites)
CREATE TABLE requisite_group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES requisite_groups(id),
    target_course_id INTEGER REFERENCES courses(id),
    target_subject VARCHAR(10), -- For loosely defined requisites
    target_catalog VARCHAR(20), -- For loosely defined requisites
    concurrent_ok BOOLEAN DEFAULT FALSE, -- For co-reqs that allow concurrent enrollment
    grade_min VARCHAR(2), -- Minimum grade required, if applicable
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((target_course_id IS NOT NULL) OR 
           (target_subject IS NOT NULL AND target_catalog IS NOT NULL))
);

-- Course Equivalents (cross-lists, substitutions)
CREATE TABLE course_equivalents (
    id SERIAL PRIMARY KEY,
    course_id_a INTEGER NOT NULL REFERENCES courses(id),
    course_id_b INTEGER NOT NULL REFERENCES courses(id),
    equivalence_type VARCHAR(50) NOT NULL, -- 'cross-list', 'substitute', 'transfer'
    effective_from DATE,
    effective_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (course_id_a != course_id_b),
    UNIQUE(course_id_a, course_id_b, equivalence_type)
);

-- Programs (majors, minors, certificates)
CREATE TABLE programs (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL, -- e.g., "CS_BS", "MATH_MINOR"
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('major', 'minor', 'certificate', 'other')),
    catalog_year VARCHAR(10) NOT NULL, -- e.g., "2024"
    school VARCHAR(100),
    total_credits_required INTEGER,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(code, catalog_year)
);

-- Requirement Blocks (hierarchical units of requirements)
CREATE TABLE requirement_blocks (
    id SERIAL PRIMARY KEY,
    program_id INTEGER NOT NULL REFERENCES programs(id),
    parent_block_id INTEGER REFERENCES requirement_blocks(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    required_credits NUMERIC(5,1),
    required_courses INTEGER,
    sequence_order INTEGER, -- Order within parent block
    rule JSONB NOT NULL, -- JSON rule DSL
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Block Course Matches (which courses can satisfy which blocks)
CREATE TABLE block_course_matches (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES requirement_blocks(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(block_id, course_id)
);

-- Course Unlocks (direct prerequisite relationships)
CREATE TABLE course_unlocks (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    unlocks_course_id INTEGER NOT NULL REFERENCES courses(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(course_id, unlocks_course_id)
);

-- Course Reachability (transitive prerequisite reach)
CREATE TABLE course_reachability (
    id SERIAL PRIMARY KEY,
    source_course_id INTEGER NOT NULL REFERENCES courses(id),
    reachable_course_id INTEGER NOT NULL REFERENCES courses(id),
    distance INTEGER NOT NULL, -- Number of prerequisite steps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_course_id, reachable_course_id)
);

-- ===============================
-- USER DATA (write-heavy state)
-- ===============================

-- Users (students)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(255) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'advisor', 'admin')),
    auth_provider VARCHAR(50),
    auth_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Programs (declared majors/minors)
CREATE TABLE user_programs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    program_id INTEGER NOT NULL REFERENCES programs(id),
    declared_date DATE,
    expected_completion DATE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, program_id)
);

-- User Preferences
CREATE TABLE preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    avg_credits_per_term INTEGER DEFAULT 15,
    max_credits_per_term INTEGER DEFAULT 18,
    prefer_morning BOOLEAN DEFAULT FALSE,
    prefer_afternoon BOOLEAN DEFAULT FALSE,
    prefer_evening BOOLEAN DEFAULT FALSE,
    prefer_compact_days BOOLEAN DEFAULT FALSE,
    prefer_spread_days BOOLEAN DEFAULT FALSE,
    day_preferences JSONB, -- Detailed preferences by day
    excluded_times JSONB, -- Times to avoid
    settings JSONB, -- Additional settings
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Completions (courses the student has earned)
CREATE TABLE completions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    term_code VARCHAR(10) REFERENCES terms(term_code),
    external_subject VARCHAR(10), -- For transfer/AP courses
    external_number VARCHAR(20), -- For transfer/AP courses
    external_title VARCHAR(255), -- For transfer/AP courses
    credits_earned NUMERIC(3,1) NOT NULL,
    grade VARCHAR(2),
    completion_type VARCHAR(20) NOT NULL CHECK (type IN ('institutional', 'transfer', 'exam', 'other')),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((course_id IS NOT NULL) OR 
           (external_subject IS NOT NULL AND external_number IS NOT NULL))
);

-- Waivers (advisor-approved exceptions)
CREATE TABLE waivers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    block_id INTEGER REFERENCES requirement_blocks(id),
    required_course_id INTEGER REFERENCES courses(id),
    substitute_course_id INTEGER REFERENCES courses(id),
    waiver_type VARCHAR(20) NOT NULL CHECK (waiver_type IN ('block', 'course', 'substitution')),
    reason TEXT,
    approved_by INTEGER REFERENCES users(id),
    approved_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (waiver_type = 'block' AND block_id IS NOT NULL) OR
        (waiver_type = 'course' AND required_course_id IS NOT NULL) OR
        (waiver_type = 'substitution' AND required_course_id IS NOT NULL AND substitute_course_id IS NOT NULL)
    )
);

-- Plans (multiple alternative degree plans)
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Plan Terms (terms within a plan)
CREATE TABLE plan_terms (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    term_code VARCHAR(10) NOT NULL REFERENCES terms(term_code),
    term_number INTEGER NOT NULL, -- e.g., 1, 2, 3, 4 for sequence
    is_final_term BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(plan_id, term_code)
);

-- Plan Items (courses in a plan term)
CREATE TABLE plan_items (
    id SERIAL PRIMARY KEY,
    plan_term_id INTEGER NOT NULL REFERENCES plan_terms(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    is_pinned BOOLEAN DEFAULT FALSE, -- User explicitly wants this course
    is_backup BOOLEAN DEFAULT FALSE, -- Alternative if primary choice unavailable
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(plan_term_id, course_id)
);

-- Audit Runs (cached degree audit results)
CREATE TABLE audit_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER REFERENCES plans(id),
    run_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'complete',
    summary JSONB,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Recommendations (cached recommendations)
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER REFERENCES plans(id),
    term_code VARCHAR(10) REFERENCES terms(term_code),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    score NUMERIC(10,5) NOT NULL, -- Higher = more recommended
    unlock_count INTEGER, -- How many courses this unlocks
    block_satisfaction JSONB, -- Which blocks this helps satisfy
    rationale TEXT, -- Explanation of recommendation
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Audit Rows (optional: import of existing advisor reports)
CREATE TABLE user_audit_rows (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    program_id INTEGER REFERENCES programs(id),
    audit_section VARCHAR(100),
    audit_text TEXT,
    raw_import JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===============================
-- INDEXES
-- ===============================

-- Catalog data indexes
CREATE INDEX idx_courses_subject_level ON courses(subject_code, level);
CREATE INDEX idx_requisite_group_members_target_course ON requisite_group_members(target_course_id);
CREATE INDEX idx_block_course_matches_course ON block_course_matches(course_id);
CREATE INDEX idx_course_unlocks_unlocks ON course_unlocks(unlocks_course_id);
CREATE INDEX idx_course_reachability_source ON course_reachability(source_course_id);
CREATE INDEX idx_course_reachability_reachable ON course_reachability(reachable_course_id);

-- User data indexes
CREATE INDEX idx_completions_user_course ON completions(user_id, course_id);
CREATE INDEX idx_plan_items_course ON plan_items(course_id);
CREATE INDEX idx_recommendations_user_term ON recommendations(user_id, term_code);
CREATE INDEX idx_recommendations_score ON recommendations(user_id, score DESC);

-- ===============================
-- TRIGGERS
-- ===============================

-- Create trigger function to enforce credit limits
CREATE OR REPLACE FUNCTION enforce_credit_limits()
RETURNS TRIGGER AS $$
DECLARE
    current_credits NUMERIC;
    is_final BOOLEAN;
BEGIN
    -- Get if this is a final term
    SELECT pt.is_final_term INTO is_final
    FROM plan_terms pt
    WHERE pt.id = NEW.plan_term_id;
    
    -- Calculate current credits in the term
    SELECT COALESCE(SUM(c.units_earned), 0) INTO current_credits
    FROM plan_items pi
    JOIN courses c ON c.id = pi.course_id
    WHERE pi.plan_term_id = NEW.plan_term_id;
    
    -- Add credits of new course
    SELECT units_earned INTO current_credits
    FROM courses
    WHERE id = NEW.course_id;
    
    -- Enforce limits: max 18 credits always, min 12 credits unless final term
    IF current_credits > 18 THEN
        RAISE EXCEPTION 'Cannot exceed 18 credits per term';
    END IF;
    
    IF NOT is_final AND current_credits < 12 THEN
        RAISE EXCEPTION 'Must have at least 12 credits in non-final terms';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on plan_items table
CREATE TRIGGER check_credit_limits
BEFORE INSERT OR UPDATE ON plan_items
FOR EACH ROW EXECUTE FUNCTION enforce_credit_limits();

-- Trigger to update the 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the update_modified_column trigger to all tables with updated_at
-- (Example for one table - repeat for all tables with updated_at)
CREATE TRIGGER update_courses_modtime
BEFORE UPDATE ON courses
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- ===============================
-- FUNCTIONS
-- ===============================

-- Function to check if a user is eligible for a course
CREATE OR REPLACE FUNCTION fn_user_eligible_courses(
    p_user_id INTEGER,
    p_plan_id INTEGER DEFAULT NULL,
    p_term_code VARCHAR DEFAULT NULL
) 
RETURNS TABLE (course_id INTEGER) AS $$
BEGIN
    -- Implementation would check:
    -- 1. Completions
    -- 2. Requisite satisfaction
    -- 3. Anti-requisite checks
    -- 4. Co-requisite pairing
    
    -- This is a placeholder - actual implementation would be more complex
    RETURN QUERY
    SELECT c.id
    FROM courses c
    WHERE NOT EXISTS (
        -- Exclude courses already completed
        SELECT 1 FROM completions comp
        WHERE comp.user_id = p_user_id AND comp.course_id = c.id
    )
    -- Add requisite logic here
    ;
END;
$$ LANGUAGE plpgsql;

-- ===============================
-- VIEW DEFINITIONS
-- ===============================

-- View to simplify course display
CREATE VIEW v_courses AS
SELECT 
    c.id,
    c.subject_code,
    c.catalog_number,
    c.subject_code || ' ' || c.catalog_number AS course_code,
    c.title,
    c.description,
    c.level,
    c.units_earned,
    c.is_offered_fall,
    c.is_offered_spring,
    c.is_offered_summer
FROM courses c;

-- View for available courses in the current term
CREATE VIEW v_current_offerings AS
SELECT
    c.id AS course_id,
    c.subject_code,
    c.catalog_number,
    c.subject_code || ' ' || c.catalog_number AS course_code,
    c.title,
    co.term_code,
    co.class_number,
    co.section_number,
    co.instructor,
    co.days_of_week,
    co.start_time,
    co.end_time,
    co.seats_available,
    co.waitlist_count
FROM course_offerings co
JOIN courses c ON c.id = co.course_id
JOIN terms t ON t.term_code = co.term_code
WHERE t.is_active = TRUE;
