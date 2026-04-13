# DATABASE_README.md

This document explains the database that powers your degree-planning and course-recommendation app. It is written so a new contributor can understand **what each table is for**, **how tables interact**, and **why certain design choices were made** (especially around requisites, planning rules, and credit limits).

---

## Big Picture

We keep everything in **one PostgreSQL database**. Conceptually, the data falls into two families:

1. **Catalog (read-mostly facts):** subjects, courses, requisites, attributes, programs/majors/minors, requirement blocks, and precomputed unlock graphs.
2. **User state (write-heavy):** students, their completions, waivers/substitutions, preferences, plans (multiple alternatives), audits, and recommendations.

A single database lets us do **fast joins** (e.g., “eligible courses that also satisfy a requirement block”) and use Postgres strengths: recursive CTEs for graph walks, full-text search, materialized views, and constraints/triggers.

---

## Key Modeling Decisions

### Requisites as Logic Groups

Requisites are messy in real catalogs. We model them as:

- `requisite_groups` (the **OR** layer): a course can have **multiple groups** per kind (pre/co/anti). Satisfying **any** group of the same kind satisfies that kind.
- `requisite_group_members` (the **AND** layer): a group contains **members** (courses/subjects) that are required **together**, unless the group uses `logic='min_count'`, in which case **any N** of the members suffice.

**Co-requisites nuance (CHEM 1601 vs 1601L):**  
If **CHEM 1601L (lab)** has **CHEM 1601 (lecture)** as a co-req, the lab gets a `requisite_groups` row with `kind='co'` and one member pointing to 1601 with `concurrent_ok = true`. This means the student can satisfy the co-req **either by having already completed 1601 or by taking 1601 in the same term**. The lecture itself has no co-req record, so students may take 1601 alone if their program doesn’t require the lab.

### Requirement Blocks & Electives

Programs are decomposed into `requirement_blocks` (e.g., “CS Core”, “Depth Electives”, “Basic Science”). A small JSON DSL in `rule` expresses constraints like “take at least 12 credits from these subjects at level ≥ 2000.” We precompute a searchable mapping of **which courses can satisfy which block** in `block_course_matches`.

### Planning & Credit Rules

Students can create multiple `plans`. Each plan has `plan_terms` (one per term in the timeline) and `plan_items` (courses in a term). Triggers enforce per-term **credit floors/caps**:

- **Default**: 12–18 credits per term
- **Final term exception**: If `plan_terms.is_final_term = true`, the **12-credit floor is waived**, but the 18-credit cap still applies.

### Unlock Graphs

To quickly surface “which course opens the most,” we precompute:

- `course_unlocks` (direct edges): If you complete **A**, **B** becomes eligible.
- `course_reachability` (transitive): From **A**, how many courses are reachable via chains of prerequisites, and in how many steps.

---

## Table-by-Table (with examples)

### `subjects`

**What:** Subject codes and names, e.g., `CHEM`, `CS`, `NESC`.  
**Why:** Normalize and link to courses.  
**Example:** `CHEM` (College of Arts & Science), `CS` (School of Engineering).

---

### `courses`

**What:** Master list of courses ever offered. Fields come from your historic CSV.  
**Key fields:** `subject_code`, `catalog_number`, `level`, `units_earned`, description.  
**Why:** Ground truth for requisites and planning; denormalized `subject_code` speeds lookups.  
**Example:**

- `CHEM 1601` (General Chemistry) — `level=1000`, `units_earned=3 or 4` per catalog.
- `CHEM 1601L` (Gen Chem Lab) — separate course with its own units and co-req to 1601.

We keep raw requisite text (`*_raw`) for auditing and manual overrides even after parsing.

---

### `terms`

**What:** Academic terms (e.g., `FA2025`, `SP2026`) with dates.  
**Why:** Time-line course offerings and plan terms.

---

### `course_offerings`

**What:** **Current-term** sections from the “this semester” CSV (`class_number`, `section_number`, etc.).  
**Why:** For short-term planning and time-conflict features later.  
**Example:** `class_number=26341`, `course_id=CHEM 1601`, `term_code=FA2025`, `section=02`.

---

### `attributes` & `course_attributes`

**What:** Tags like AXLE categories (HCA, INT, US), writing (“W”), etc.  
**Why:** Filter electives and satisfy blocks like “3 hours HCA”.

---

### `requisite_groups` & `requisite_group_members`

**What:** The requisite graph.

- `requisite_groups`: One row per **group** per **kind** (`pre`, `co`, `anti`) per **gated course**.
  - `logic='all'` → all members required; `logic='min_count'` → require `min_count` members.
- `requisite_group_members`: The **members** in a group. Prefer linking to `target_course_id`. Fallback to (`target_subject`, `target_catalog`), a.k.a. “MATH 1300”.

**Examples:**

1. **CS 2212** “requires **MATH 2410 OR MATH 2501**”:

   - One `requisite_groups` row (`kind='pre'`, `logic='min_count'`, `min_count=1`)
   - Two members: `MATH 2410`, `MATH 2501`.

2. **CHEM 1601L** “co-req **CHEM 1601** (can be concurrent)”:

   - One `requisite_groups` row (`kind='co'`, `logic='all'`)
   - One member: `CHEM 1601` with `concurrent_ok=true`.

3. **ANTI-req** “cannot take **MATH 1300** after **AP Calculus** credit”:
   - `kind='anti'` group with member representing the AP equivalency (often modeled via `course_equivalents` or a special “AP CALC” pseudo-course).

---

### `course_equivalents`

**What:** Cross-lists, substitutions, equivalencies.  
**Why:** Count one course as another (e.g., “NESC 3200” counts as “PSY 3200”).  
**Tip:** Store symmetric pairs or mirror during ETL.

---

### `programs`

**What:** Majors, minors, certificates with catalog year.  
**Example:** `CS_BS 2024`, `NESC_BS 2024`, `MATH_MINOR 2024`.

---

### `requirement_blocks`

**What:** Hierarchical units of requirements with a JSON rule DSL.  
**Examples:**

- **“CS Core”** block rule: `{"type":"all", "of":[{"course":"CS 2201"}, {"course":"CS 2212"}]}`
- **“Basic Science 12 hrs”**: `{"type":"min_credits","credits":12,"filter":{"subject_in":["BSCI","CHEM","PHYS"], "levels":[1000,2999]}}`
- **“Depth: 15 hrs 3000+”**: `{"type":"min_credits","credits":15,"filter":{"subject":"CS","level_min":3000},"limit_course_exclusions":["CS 3262"]}`

---

### `block_course_matches`

**What:** Precomputed many-to-many of which courses can satisfy which blocks.  
**Why:** Fast elective search and overlap calculations for multi-major optimization.

---

### `course_unlocks` & `course_reachability`

**What:** Precomputed graphs.

- `course_unlocks`: **Direct** edges, e.g., “MATH 1300 → MATH 1301”
- `course_reachability`: **Transitive** reach with `distance`, e.g., `MATH 1300 → (2 steps) → MATH 2300`

**Why:** Rank candidates by how much they unblock the path to graduation.

---

### `users`, `user_programs`, `preferences`

**What:** Student identities, their declared majors/minors, and planning preferences.  
**Example preferences:** `avg_credits_per_term=15`, `prefer_compact_days=true`, pinned picks per term.

---

### `completions`

**What:** Courses the student has earned (institutional, transfer, AP/IB, test).  
**Why:** Drives eligibility calculations and block satisfaction.

---

### `waivers`

**What:** Advisor-approved exceptions: waive an entire block, waive a specific required course, or substitute one course for another for this user.  
**Example:** Waive “Writing W” block because an external course already met it; substitute `MATH 2501` for `MATH 2410`.

---

### `plans`, `plan_terms`, `plan_items`

**What:** Multiple alternative degree plans; per-term flags (final term) and scheduled courses.  
**Credit rules:** Triggers enforce **12–18 per term**, except a **final term** can be **<12** but never >18.

---

### `audit_runs` & `recommendations`

**What:** Cached outputs from the audit/solver engines.  
**Why:** Speed. Also make results explainable (“why this suggestion?”).

---

### `user_audit_rows` (optional)

**What:** Raw import of your existing advisor report for reconciliation during migration.

---

## Common Questions

- **Why one DB?** Simpler joins, transactions, and caching. If read traffic grows, add a **read compute** or **replica** without changing the model.
- **How do co-reqs really work?** Co-req **belongs to the course that needs the other**. The lab needs the lecture (not vice-versa). We enforce that by placing a `kind='co'` group on the lab pointing to the lecture with `concurrent_ok=true`.
- **What about time conflicts?** We store `course_offerings.meta` (times/rooms). A future iteration can add `meeting_patterns` for conflict checking in SQL.

# PLANNING_ALGOS_README.md

This guide shows **how to compute the key user flows** using the database: fastest path to graduation, short-term/long-term gap fills, maximize majors/minors, and identify biggest blockers. It includes algorithm outlines and SQL building blocks.

---

## Shared Concepts

- **Eligibility**: A course is eligible when:

  1. Each `kind='pre'` has **at least one group** satisfied, where a group is satisfied if:
     - `logic='all'` and **all** its members are completed (or, if `concurrent_ok`, planned in the same term), or
     - `logic='min_count'` and at least `min_count` members are completed/planned as allowed.
  2. No `kind='anti'` group matches.
  3. For the **actual term schedule**, co-reqs are satisfied by **either prior completion or same-term pairing**.

- **Required vs Electives**: Required courses are those present in requirement blocks that must be satisfied. Electives are courses that can satisfy a block but are not fixed.

- **Unlock score**: Quantifies how much a candidate course opens downstream:

  - **Direct unlocks** = count of remaining required courses that appear in `course_unlocks` from this course.
  - **Transitive unlocks** = sum of `1/distance` over `course_reachability` into remaining required courses.
  - Weight required > desired > elective (e.g., 3:2:1).

- **Credit rules**: 12–18 per term, except `plan_terms.is_final_term = true` allows <12 but never >18 (enforced by triggers in the DB).

---

## I) What should I take next to graduate ASAP?

**Goal:** Recommend the most impactful next courses given the student’s programs, completions, waivers, and preferences.

**Steps:**

1. **Remaining set `R`**: From `user_programs → requirement_blocks → block_course_matches`, gather all courses that can satisfy unsatisfied blocks; subtract those already satisfied by `completions` and `waivers`.
2. **Eligible now**: Compute courses the student can take next term (or generically “now”) following the eligibility rules.
3. **Score**: For each eligible course, compute:
   - `direct_score = COUNT(DISTINCT unlocks_course_id ∩ R)`
   - `transitive_score = SUM(1/distance)` over `course_reachability` into `R`
   - `block_fit_bonus` for courses that immediately satisfy a nearly complete block (e.g., remaining 3 credits).
4. **Rank and explain**: Sort by weighted total. Show “CS 2201 → unlocks CS 3251; MATH 1300 → 1301 → 2300 chain.”

**SQL sketch (direct unlocks vs remaining):**

```sql
WITH remaining AS (
  SELECT DISTINCT bcm.course_id
  FROM user_programs up
  JOIN requirement_blocks rb ON rb.program_id = up.program_id
  JOIN block_course_matches bcm ON bcm.block_id = rb.id
  WHERE up.user_id = $1
  -- TODO: minus satisfied via completions/waivers
),
eligible AS (
  -- TODO: set-returning fn_user_eligible_courses($1, $plan_id, $term_code)
  SELECT course_id FROM fn_user_eligible_courses($1, $2, $3)
),
score AS (
  SELECT e.course_id, COUNT(DISTINCT cu.unlocks_course_id) AS direct_unlocks
  FROM eligible e
  LEFT JOIN course_unlocks cu ON cu.course_id = e.course_id
  JOIN remaining r ON r.course_id = cu.unlocks_course_id
  GROUP BY e.course_id
)
SELECT * FROM score ORDER BY direct_unlocks DESC LIMIT 20;
```

---

## II) Fill gaps this semester (short-term vs long-term)

**Short-term (THIS term):**

- Intersect `eligible` with `course_offerings` for the target `term_code`.
- Greedy fill to **12–18 credits**:

  1. Place **must-take** (advisor/user-pinned) courses.
  2. Add highest unlock-score courses that also help satisfy blocks near completion.
  3. Respect co-req pairing (`concurrent_ok`) and avoid anti-req conflicts.

**Long-term (multi-term):**

- Consider **seasonality** (`course_offerings` + `courses.term_offered_raw`).
- Simulate the next 2–4 terms: choose high unlock-score courses now to unlock rare/FA-only courses later.
- Keep **2–3 alternative** plans (required-first, balanced load, interest-weighted).

---

## III) Maximize majors/minors under current required schedule

**Idea:** Treat each targeted program’s remaining blocks as sets and find permutations of additional programs that add the **fewest new courses** (set-cover flavor) under credit and term limits.

**Steps:**

1. Lock in the student’s current required courses (write to `plans`/`plan_terms`/`plan_items`).
2. Pick candidate additional programs (majors/minors) by **overlap potential**: count intersections of `block_course_matches`.
3. For each permutation (limit to top \~10 by greedy pre-ranking):

   - Compute additional courses needed beyond the plan.
   - Simulate scheduling across remaining terms (12–18 credits; allow 5th year if user opts in).
   - Score: `3*majors + 1*minors - 0.1*extra_courses + headroom_bonus`.

4. Return the top permutations and allow the user to “project my 4-year schedule” into a new `plan`.

---

## IV) Biggest blockers

**Define priorities:**

- **TOP:** blockers that gate **required** downstream courses.
- **MID:** blockers that gate **desired** (user-pinned) non-required courses.
- **LOW:** blockers that mainly gate electives.
  If a blocker qualifies as both TOP and MID, **treat as TOP**.

**Compute:**

1. For each unsatisfied required course `R`, compute its **prereq frontier** (the minimal set of unmet prereq members).
2. Count how many required/desired/elective courses each frontier node unlocks (using `course_reachability`).
3. Rank by `(100*required + 10*desired + elective)`.

**Sketch:**

```sql
-- frontier(blocker_course_id) depends on your eligibility implementation.
-- Once you have frontier, aggregate impact:
WITH agg AS (
  SELECT f.blocker_course_id,
         SUM(CASE WHEN r.is_required THEN 1 ELSE 0 END) AS req_unlocked,
         SUM(CASE WHEN r.is_desired  THEN 1 ELSE 0 END) AS des_unlocked,
         SUM(CASE WHEN r.is_elective THEN 1 ELSE 0 END) AS elec_unlocked
  FROM frontier f
  JOIN course_reachability cr ON cr.source_course_id = f.blocker_course_id
  JOIN remaining_courses r ON r.course_id = cr.reachable_course_id
  GROUP BY f.blocker_course_id
)
SELECT *,
  CASE WHEN req_unlocked > 0 THEN 'TOP'
       WHEN des_unlocked > 0 THEN 'MID'
       ELSE 'LOW' END AS priority
FROM agg
ORDER BY (req_unlocked*100 + des_unlocked*10 + elec_unlocked) DESC
LIMIT 50;
```

---

## Performance & Caching

- Refresh `block_course_matches`, `course_unlocks`, `course_reachability` nightly or on catalog changes.
- Cache solver results in `recommendations` and `audit_runs` keyed by a hash of inputs (programs + completions + plan constraints).
- Put 60–300s edge caching in front of read-heavy endpoints (`/eligible`, `/recommendations`).

---

Below are the **SQL functions and ETL stubs** we discussed. They are drafts you can refine as you integrate your parser and UI.

```sql
-- =========================================================
-- sql/functions.sql
-- Helper functions for eligibility, unlock scoring, and utilities
-- =========================================================

-- Normalize numeric level from catalog_number, e.g., '2410' -> 2000 level
CREATE OR REPLACE FUNCTION fn_level_from_catalog_number(p_catalog TEXT)
RETURNS INT
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  n INT;
BEGIN
  -- Extract leading digits; fallback 0
  n := NULLIF(regexp_replace(p_catalog, '[^0-9]', '', 'g'), '')::INT;
  IF n IS NULL THEN
    RETURN NULL;
  END IF;
  RETURN (n/1000)*1000; -- 2410 -> 2000 level bucket
END;
$$;

-- Utility: has the user completed a specific course (or an equivalent)?
CREATE OR REPLACE FUNCTION fn_user_has_course(user_id UUID, course_id BIGINT)
RETURNS BOOLEAN
LANGUAGE sql STABLE AS $$
  WITH eq AS (
    SELECT equivalent_course_id AS cid FROM course_equivalents WHERE course_id = $2
    UNION
    SELECT course_id AS cid FROM course_equivalents WHERE equivalent_course_id = $2
    UNION
    SELECT $2::bigint
  )
  SELECT EXISTS (
    SELECT 1 FROM completions c
    JOIN eq ON eq.cid = c.course_id
    WHERE c.user_id = $1
  );
$$;

-- Utility: does a waiver satisfy a specific course requirement for this user?
CREATE OR REPLACE FUNCTION fn_user_has_waiver_for_course(user_id UUID, course_id BIGINT)
RETURNS BOOLEAN
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM waivers w
    WHERE w.user_id = $1
      AND (w.course_id = $2 OR w.substitute_course_id = $2)
  );
$$;

-- Evaluate whether a single requisite group (one OR candidate) is satisfied.
-- If checking for a specific plan/term, allow concurrent_ok for that term.
CREATE OR REPLACE FUNCTION fn_group_satisfied(
  p_user_id  UUID,
  p_group_id BIGINT,
  p_plan_id  BIGINT,
  p_term_code TEXT
) RETURNS BOOLEAN
LANGUAGE plpgsql STABLE AS $$
DECLARE
  v_logic group_logic;
  v_min_count INT;
  v_need INT;
  v_have INT := 0;
  r RECORD;
  v_taken_same_term BOOLEAN;
BEGIN
  SELECT logic, min_count INTO v_logic, v_min_count
  FROM requisite_groups WHERE id = p_group_id;

  v_need := COALESCE(v_min_count, 0);

  FOR r IN
    SELECT m.*, m.target_course_id AS cid
    FROM requisite_group_members m
    WHERE m.group_id = p_group_id
  LOOP
    -- Is this member satisfied?
    -- 1) completed (including equivalents or waivers)
    IF fn_user_has_course(p_user_id, r.cid) OR fn_user_has_waiver_for_course(p_user_id, r.cid) THEN
      v_have := v_have + 1;
      CONTINUE;
    END IF;

    -- 2) If concurrent_ok and we are evaluating a specific term, check if planned same term
    IF r.concurrent_ok AND p_term_code IS NOT NULL AND p_plan_id IS NOT NULL THEN
      SELECT EXISTS (
        SELECT 1 FROM plan_items pi
        WHERE pi.plan_id = p_plan_id
          AND pi.term_code = p_term_code
          AND pi.course_id = r.cid
      ) INTO v_taken_same_term;

      IF v_taken_same_term THEN
        v_have := v_have + 1;
        CONTINUE;
      END IF;
    END IF;

    -- 3) Fallback: subject/catalog text match (if we couldn't resolve target_course_id)
    IF r.target_course_id IS NULL AND r.target_subject IS NOT NULL AND r.target_catalog IS NOT NULL THEN
      SELECT EXISTS (
        SELECT 1 FROM completions c
        JOIN courses x ON x.id = c.course_id
        WHERE c.user_id = p_user_id
          AND x.subject_code = r.target_subject
          AND x.catalog_number = r.target_catalog
      ) INTO v_taken_same_term; -- reuse var
      IF v_taken_same_term THEN
        v_have := v_have + 1;
        CONTINUE;
      END IF;
    END IF;

    -- If logic=all, any unsatisfied member fails the group
    IF v_logic = 'all' THEN
      RETURN FALSE;
    END IF;
  END LOOP;

  IF v_logic = 'all' THEN
    -- all members must have been satisfied (we only arrive here if none failed)
    RETURN TRUE;
  ELSE
    -- min_count logic
    RETURN v_have >= v_need;
  END IF;
END;
$$;

-- Check that ALL 'pre' kinds are satisfied for a course; reject if any 'anti' matches.
CREATE OR REPLACE FUNCTION fn_is_course_eligible(
  p_user_id   UUID,
  p_course_id BIGINT,
  p_plan_id   BIGINT DEFAULT NULL,
  p_term_code TEXT   DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql STABLE AS $$
DECLARE
  g RECORD;
  ok BOOLEAN;
BEGIN
  -- Anti-req: if ANY anti group is satisfied, not eligible
  FOR g IN
    SELECT id FROM requisite_groups WHERE course_id = p_course_id AND kind = 'anti'
  LOOP
    ok := fn_group_satisfied(p_user_id, g.id, p_plan_id, p_term_code);
    IF ok THEN
      RETURN FALSE;
    END IF;
  END LOOP;

  -- Pre-req: for EACH 'pre' requirement, at least ONE group must be satisfied
  FOR g IN
    SELECT id FROM requisite_groups WHERE course_id = p_course_id AND kind = 'pre'
  LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM requisite_groups rg
      WHERE rg.course_id = p_course_id AND rg.kind = 'pre'
        AND fn_group_satisfied(p_user_id, rg.id, p_plan_id, p_term_code)
    ) THEN
      RETURN FALSE;
    END IF;
  END LOOP;

  RETURN TRUE;
END;
$$;

-- Set-returning helper: all eligible courses for a user (optionally for a plan/term)
CREATE OR REPLACE FUNCTION fn_user_eligible_courses(
  p_user_id   UUID,
  p_plan_id   BIGINT DEFAULT NULL,
  p_term_code TEXT   DEFAULT NULL
) RETURNS TABLE(course_id BIGINT)
LANGUAGE sql STABLE AS $$
  SELECT c.id
  FROM courses c
  WHERE fn_is_course_eligible(p_user_id, c.id, p_plan_id, p_term_code);
$$;

-- Compute direct/transitive unlock scores against remaining required courses.
-- You can weight and extend this as needed.
CREATE OR REPLACE FUNCTION fn_unlock_scores_for_user(
  p_user_id UUID
) RETURNS TABLE(course_id BIGINT, direct_score INT, transitive_score NUMERIC)
LANGUAGE sql STABLE AS $$
WITH remaining AS (
  SELECT DISTINCT bcm.course_id
  FROM user_programs up
  JOIN requirement_blocks rb ON rb.program_id = up.program_id
  JOIN block_course_matches bcm ON bcm.block_id = rb.id
  WHERE up.user_id = p_user_id
  -- minus already satisfied by completions/waivers (left as exercise)
),
eligible AS (
  SELECT c.id AS course_id
  FROM courses c
  WHERE fn_is_course_eligible(p_user_id, c.id, NULL, NULL)
),
d AS (
  SELECT e.course_id, COUNT(DISTINCT cu.unlocks_course_id) AS direct_score
  FROM eligible e
  LEFT JOIN course_unlocks cu ON cu.course_id = e.course_id
  JOIN remaining r ON r.course_id = cu.unlocks_course_id
  GROUP BY e.course_id
),
t AS (
  SELECT e.course_id, COALESCE(SUM(1.0 / NULLIF(cr.distance,0)), 0) AS transitive_score
  FROM eligible e
  JOIN course_reachability cr ON cr.source_course_id = e.course_id
  JOIN remaining r ON r.course_id = cr.reachable_course_id
  GROUP BY e.course_id
)
SELECT e.course_id, COALESCE(d.direct_score,0), COALESCE(t.transitive_score,0)
FROM eligible e
LEFT JOIN d USING (course_id)
LEFT JOIN t USING (course_id);
$$;
```

```sql
-- =========================================================
-- sql/etl_seed.sql
-- Staging + seed load from your three CSV formats
-- =========================================================

-- 1) Historic catalog CSV
-- Columns:
-- course_id,subject,catalogNumber,displayName,longTitle,schoolCode,careerCode,componentCode,unitsEarned,termOffered,Allreqs,coReqs,preReqs,antiReqs,attributes,description

CREATE TEMP TABLE stg_courses_hist (
  course_id BIGINT,
  subject TEXT,
  catalogNumber TEXT,
  displayName TEXT,
  longTitle TEXT,
  schoolCode TEXT,
  careerCode TEXT,
  componentCode TEXT,
  unitsEarned NUMERIC,
  termOffered TEXT,
  Allreqs TEXT,
  coReqs TEXT,
  preReqs TEXT,
  antiReqs TEXT,
  attributes TEXT,
  description TEXT
);

-- Example:
-- COPY stg_courses_hist FROM '/path/courses_hist.csv' CSV HEADER;

-- Upsert subjects
INSERT INTO subjects(code)
SELECT DISTINCT subject
FROM stg_courses_hist
ON CONFLICT (code) DO NOTHING;

-- Upsert courses
INSERT INTO courses (
  id, subject_id, subject_code, catalog_number, level,
  display_name, long_title, school_code, career_code, component_code,
  units_earned, description, term_offered_raw,
  all_reqs_raw, co_reqs_raw, pre_reqs_raw, anti_reqs_raw
)
SELECT
  s.course_id,
  subj.id,
  s.subject,
  s.catalogNumber,
  fn_level_from_catalog_number(s.catalogNumber),
  s.displayName,
  s.longTitle,
  s.schoolCode,
  s.careerCode,
  s.componentCode,
  s.unitsEarned,
  s.description,
  s.termOffered,
  s.Allreqs,
  s.coReqs,
  s.preReqs,
  s.antiReqs
FROM stg_courses_hist s
JOIN subjects subj ON subj.code = s.subject
ON CONFLICT (id) DO UPDATE SET
  subject_id = EXCLUDED.subject_id,
  subject_code = EXCLUDED.subject_code,
  catalog_number = EXCLUDED.catalog_number,
  level = EXCLUDED.level,
  display_name = EXCLUDED.display_name,
  long_title = EXCLUDED.long_title,
  school_code = EXCLUDED.school_code,
  career_code = EXCLUDED.career_code,
  component_code = EXCLUDED.component_code,
  units_earned = EXCLUDED.units_earned,
  description = EXCLUDED.description,
  term_offered_raw = EXCLUDED.term_offered_raw,
  all_reqs_raw = EXCLUDED.all_reqs_raw,
  co_reqs_raw = EXCLUDED.co_reqs_raw,
  pre_reqs_raw = EXCLUDED.pre_reqs_raw,
  anti_reqs_raw = EXCLUDED.anti_reqs_raw;

-- Attributes (split by comma/space)
-- This assumes attributes like "HCA, INT". Adjust split logic to your format.
WITH exploded AS (
  SELECT c.id AS course_id, trim(unnest(string_to_array(stg.attributes, ','))) AS code
  FROM stg_courses_hist stg
  JOIN courses c ON c.id = stg.course_id
  WHERE stg.attributes IS NOT NULL AND stg.attributes <> ''
)
INSERT INTO attributes(code)
SELECT DISTINCT code FROM exploded
ON CONFLICT (code) DO NOTHING;

INSERT INTO course_attributes(course_id, attr_code)
SELECT e.course_id, e.code
FROM exploded e
ON CONFLICT DO NOTHING;

-- 2) Current-term offerings CSV
-- Columns: classNumber,displayName,longTitle,subject,catalogNumber,section_number,schoolCode,careerCode,componentCode,unitsEarned

CREATE TEMP TABLE stg_offerings_cur (
  classNumber TEXT,
  displayName TEXT,
  longTitle TEXT,
  subject TEXT,
  catalogNumber TEXT,
  section_number TEXT,
  schoolCode TEXT,
  careerCode TEXT,
  componentCode TEXT,
  unitsEarned NUMERIC,
  term_code TEXT  -- add this column during load (e.g., 'FA2025')
);

-- COPY stg_offerings_cur FROM '/path/offerings_cur.csv' CSV HEADER;

-- Ensure term exists
INSERT INTO terms(code)
SELECT DISTINCT term_code FROM stg_offerings_cur
ON CONFLICT (code) DO NOTHING;

-- Upsert offerings; join to courses by subject+catalog
INSERT INTO course_offerings(
  class_number, course_id, term_code, section_number,
  display_name, long_title, school_code, career_code, component_code, units_earned
)
SELECT
  s.classNumber,
  c.id,
  s.term_code,
  s.section_number,
  s.displayName,
  s.longTitle,
  s.schoolCode,
  s.careerCode,
  s.componentCode,
  s.unitsEarned
FROM stg_offerings_cur s
JOIN courses c
  ON c.subject_code = s.subject AND c.catalog_number = s.catalogNumber
ON CONFLICT (class_number) DO NOTHING;

-- 3) Advisor/degree audit CSV (optional migration aid)
-- Columns: groupName,isMainReq,name,description,status,requirementGroupNumber,requirementGroupNumber2,entrySequence,entrySequence2,unitsRequired,unitsUsed,unitsNeeded

CREATE TEMP TABLE stg_user_audit (
  user_email TEXT,
  groupName TEXT,
  isMainReq BOOLEAN,
  name TEXT,
  description TEXT,
  status TEXT,
  requirementGroupNumber TEXT,
  requirementGroupNumber2 TEXT,
  entrySequence INT,
  entrySequence2 INT,
  unitsRequired NUMERIC,
  unitsUsed NUMERIC,
  unitsNeeded NUMERIC
);

-- COPY stg_user_audit FROM '/path/user_audit.csv' CSV HEADER;

INSERT INTO user_audit_rows(
  user_id, group_name, is_main_req, name, description, status,
  requirement_group_number, requirement_group_number2,
  entry_sequence, entry_sequence2, units_required, units_used, units_needed
)
SELECT
  u.id,
  s.groupName,
  s.isMainReq,
  s.name,
  s.description,
  s.status,
  s.requirementGroupNumber,
  s.requirementGroupNumber2,
  s.entrySequence,
  s.entrySequence2,
  s.unitsRequired,
  s.unitsUsed,
  s.unitsNeeded
FROM stg_user_audit s
JOIN users u ON u.email = s.user_email;
```

# DEPLOYMENT_README.md

## Goal

Stand up the database and API with **fast reads**, **safe writes**, and **$0–cheap** hosting.

---

## Database

### Option A: Neon (serverless Postgres)

- Create a Neon project.
- Run the DDL (schema) in the SQL editor.
- Use the **serverless HTTP driver** (`@neondatabase/serverless`) from your edge functions (prevents connection pool exhaustion).
- Add a **read compute** later if read traffic grows; no schema changes required.

### Option B: Supabase (Postgres + Auth + RLS)

- Create a project; run the DDL in SQL Editor.
- Turn on **Row Level Security** for user-owned tables.
- Use **Edge Functions** if you want serverless compute close to users.
- Supabase Studio gives you a built-in ERD and data browser.

---

## API (Edge)

- **Cloudflare Workers** or **Vercel Edge Functions**.
- Connect using Neon’s serverless driver or pg-wire via pooled proxy (if not on edge).
- Expose endpoints:
  - `GET /eligible?user=...&term=...`
  - `GET /recommendations?user=...`
  - `POST /plans` (create plan)
  - `POST /plan_items` (add course to term)
- Add **cache control** headers and use the platform’s cache (`caches.default`) for read endpoints: `Cache-Control: s-maxage=300, stale-while-revalidate=86400`.

---

## Jobs & Refresh

- Use **Cloudflare Cron Triggers** / **Vercel Cron** / **GitHub Actions** to refresh:
  - `block_course_matches`
  - `course_unlocks`
  - `course_reachability`
- Schedule nightly or on ETL events.

---

## Observability & Cost

- Enable `pg_stat_statements`, watch slow queries, add indexes/materialized views as needed.
- Keep writes moderate; cache read endpoints; you should comfortably serve **hundreds of lookups/min** on free tiers.
