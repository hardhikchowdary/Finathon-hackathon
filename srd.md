# SRD: Dynamic Skill Graph & Internal Talent Marketplace (MVP Build Spec)

**Audience:** an AI coding agent (Antigravity) and the human team supervising it.
**Goal:** a working, demo-ready MVP in a 36-hour hackathon. Scope is deliberately narrow. Do not add features, services or dependencies that are not listed here.

---

## 0. How the agent must work

1. Build **phase by phase** (Section 12). Finish and verify each phase before starting the next.
2. After each phase: run the tests listed for it, start the app, and confirm the phase's "Done when" checks. If a browser tool is available, verify UI pages visually.
3. Commit after each phase with message `phase-N: <summary>`.
4. Follow the API contracts in Section 8 **exactly** (field names, types). The frontend depends on them.
5. Keep every scoring number **configurable** in `backend/app/config.py`. Do not hard-code weights inside functions.
6. Never invent facts in LLM output. The LLM only parses queries and phrases explanations from computed data (Section 9).
7. If something is ambiguous, choose the simplest option that satisfies the acceptance criteria (Section 13) and note the decision in `DECISIONS.md`.

---

## 1. Product summary

Companies hire externally for skills they already have because nobody knows who has actually done what. This app builds a **skill graph from evidence of work** (projects, certifications, training), estimates **proficiency with visible evidence**, answers **natural-language staffing queries** with ranked, explained candidates, finds **near-qualified employees** with **personalized upskilling paths**, and updates everything **live** when new evidence is added.

**Demo query:** "Find employees capable of building a React + Node.js fintech application."

### In scope (MVP)
Synthetic data, skill taxonomy with synonyms, skill extraction from text, skill graph, proficiency estimation with evidence, natural-language search with explanations, near-qualified matching, upskilling paths, add-evidence with live recalculation, graph visualization, coverage dashboard.

### Stretch (only after all acceptance criteria pass)
Internal marketplace: openings, express interest, ranked matches.

### Out of scope
Authentication/SSO, RBAC, audit logs, real HRIS/Git/LMS integrations, Neo4j, Redis, Celery, Docker/Kubernetes, mobile apps, email notifications.

---

## 2. Technology stack (fixed)

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Uvicorn |
| Database | SQLite (single file `backend/data/app.db`) |
| Graph logic | NetworkX (built from DB on demand) for graph endpoint and traversal; SQL for everything else |
| LLM | Anthropic API via the official `anthropic` Python SDK. Model from env `CLAUDE_MODEL` (default `claude-sonnet-5-5`). |
| NLP (extraction) | Rule-based matching over taxonomy + synonyms (no heavy ML libraries). LLM used only as fallback for unmatched terms, if `ANTHROPIC_API_KEY` is set. |
| Frontend | React 18 + TypeScript + Vite, Tailwind CSS, React Router, TanStack Query, Cytoscape.js (`react-cytoscapejs`), Recharts |
| Testing | pytest (backend), Vitest optional (frontend) |
| Runtime | Backend on port 8000, frontend on port 5173 with Vite proxy `/api` → `http://localhost:8000` |

**Environment variables:** `ANTHROPIC_API_KEY` (optional), `CLAUDE_MODEL`, `REFERENCE_DATE` (optional ISO date, defaults to today).

**No API key behavior:** the system must fully work without an LLM using the rule-based parser and template explanations (Section 9.4). Responses report which mode was used.

---

## 3. Repository structure

```
/
├── SRD.md
├── DECISIONS.md
├── README.md                # run instructions
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, router registration
│   │   ├── config.py        # all weights, thresholds, half-lives
│   │   ├── db.py            # engine, session
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic response/request models
│   │   ├── routers/         # search.py, employees.py, evidence.py, graph.py,
│   │   │                    # dashboard.py, near_qualified.py, admin.py, marketplace.py
│   │   ├── services/
│   │   │   ├── taxonomy.py      # synonym matching
│   │   │   ├── extraction.py    # text -> skills
│   │   │   ├── proficiency.py   # scoring engine
│   │   │   ├── ranking.py       # candidate ranking
│   │   │   ├── near_qualified.py
│   │   │   ├── upskilling.py
│   │   │   ├── llm.py           # parse + explain + cache + fallback
│   │   │   └── graph.py         # NetworkX builders
│   │   └── seed/
│   │       ├── taxonomy.json
│   │       ├── courses.json
│   │       └── seed.py          # deterministic data generator
│   └── tests/
└── frontend/
    └── src/ (pages/, components/, api/, types/)
```

---

## 4. Domain model (SQLite tables)

| Table | Key columns |
|---|---|
| `employee` | id, name, email, role, department, level (`Junior/Mid/Senior/Lead`), location, manager_id |
| `skill` | id, name, category, half_life_months (nullable, overrides default) |
| `skill_alias` | skill_id, alias (lowercase, unique) |
| `skill_relation` | skill_a_id, skill_b_id, strength (0-1) (treat as symmetric) |
| `domain` | id, name (e.g. fintech), keywords (JSON list) |
| `project` | id, name, description (free text), domain_id, complexity (1-5), start_date, end_date (null = ongoing), `_truth_skills` (JSON list of skill ids, used **only** by tests) |
| `project_skill` | project_id, skill_id, confidence, source (`extracted`/`manual`) |
| `assignment` | id, employee_id, project_id, role (`Contributor/Lead/Architect`), allocation_pct, start_date, end_date |
| `certification` | id, name, issuer, skill_ids (JSON) |
| `employee_certification` | employee_id, certification_id, issued_on, expires_on (nullable) |
| `training_record` | id, employee_id, course_name, skill_ids (JSON), completed_on |
| `self_declared_skill` | employee_id, skill_id |
| `evidence` | id, employee_id, skill_id, source_type (`project/certification/training/self_declared`), source_id, weight, occurred_on, description |
| `proficiency` | employee_id, skill_id, score (0-100), level, verified (bool), breakdown (JSON), computed_at |
| `course` | id, title, provider, skill_id, from_level, to_level, hours, points_gain |
| `llm_cache` | key (hash), response (JSON), created_at |
| `opening`, `interest` | (stretch) opening: id, title, owner_id, required_skills (JSON), start_date, status; interest: opening_id, employee_id, created_at |

`evidence` rows are **derived**: they are regenerated whenever a project assignment, certification, training record or self-declaration changes.

---

## 5. Taxonomy and synthetic data

### 5.1 Taxonomy (`seed/taxonomy.json`)
About 60 skills across categories: Language, Frontend, Backend, Data/AI, Cloud/DevOps, Security, Mobile, Quality, Practice. Must include at least:
Python, JavaScript, TypeScript, Java, Go, SQL, React, Next.js, Vue, Angular, HTML/CSS, Redux, Tailwind CSS, Node.js, Express, Django, FastAPI, Spring Boot, GraphQL, REST API Design, Microservices, PostgreSQL, MongoDB, Redis, Kafka, Machine Learning, NLP, Data Visualization, AWS, Azure, GCP, Docker, Kubernetes, Terraform, CI/CD, Application Security, PCI-DSS, OAuth/OIDC, Payments Integration, React Native, Flutter, Test Automation, Playwright, Performance Testing, System Design, Agile/Scrum, Technical Leadership.

Each of the top 30 skills has at least 3 aliases (e.g. React: `reactjs`, `react.js`, `react js`; Node.js: `nodejs`, `node`, `node js`; Kubernetes: `k8s`; PostgreSQL: `postgres`).

**Domains:** fintech (keywords: payments, banking, wallet, ledger, lending, kyc, upi, trading), healthcare, e-commerce, logistics, insurance, telecom, edtech.

**Relations (examples, strength):** React–Next.js 0.7, React–Redux 0.6, React–TypeScript 0.4, Node.js–Express 0.7, Node.js–TypeScript 0.4, Node.js–JavaScript 0.6, Payments Integration–PCI-DSS 0.6, Payments Integration–REST API Design 0.4, Docker–Kubernetes 0.6, PostgreSQL–SQL 0.7. Add about 40 more.

### 5.2 Generator (`seed/seed.py`)
Deterministic (`random.seed(42)`), dates relative to `REFERENCE_DATE`. Command: `python -m app.seed.seed` recreates the DB.

- **100 employees** across departments: Frontend, Backend, Platform, Data, QA, Security, Product. Realistic mixed names.
- **40 projects**, 6-24 months long, spanning the last 5 years. `description` is **free text written with varied wording and synonyms** (e.g. "built the customer dashboard using ReactJS and a NodeJS/Express API") so extraction is genuinely exercised. `_truth_skills` records the real stack.
- 2-6 assignments per employee, with roles and allocation percentages. Current utilization = sum of allocation_pct for assignments active at the reference date (cap display at 100).
- About 25 certifications, 60 training records, 300 self-declared skills (deliberately noisy, some with no evidence).
- 25 courses in `courses.json` covering the most-needed skills (with `hours`, `points_gain` between 8 and 20).

### 5.3 Planted demo scenarios (mandatory, verify with tests)

| Employee | Story | Expected behavior |
|---|---|---|
| Ananya Rao | React lead on 3 recent projects, Node.js on 2, 2 fintech projects, utilization ~30% | Rank 1 for the demo query |
| Rohan Iyer | Strong Node.js lead, React on 2 projects, 1 fintech project, utilization ~90% | Top 3 but penalized for availability |
| Meera Nair | Solid React and Node.js, **no fintech, no Payments Integration/PCI-DSS** | Near-qualified; gap = fintech domain + Payments Integration |
| Karthik Reddy | Strong React, Node.js weak (one old small project) | Near-qualified; gap = Node.js |
| Sana Khan | Self-declares React, Node.js and fintech, **no evidence** | Ranks low; skills shown "unverified" |
| Vikram Shah | Heavy React 4+ years ago, nothing since | Lower than recent experts (recency decay visible) |
| Divya Menon | Node.js expert, utilization ~60% | Suggested as **mentor** for Node.js gaps |
| Arjun Patel | Java backend with Payments Integration and PCI-DSS, no React | Strong domain fit, low skill fit |

**Live-update scenario:** adding the project "Wallet Payments Redesign" (complexity 4, description mentioning React, Node.js, payment gateway integration and PCI compliance, domain fintech, role Lead) to **Meera Nair** must raise her Payments Integration score and move her up in the demo query ranking by at least 3 places. Tune the seed data so this holds.

---

## 6. Core algorithms (all parameters in `config.py`)

### 6.1 Proficiency (per employee, per skill)
For each evidence item `e`:

```
contribution(e) = BASE[source_type] × complexity_factor × role_factor × decay
BASE = {project: 10, certification: 8, training: 4, self_declared: 2}
complexity_factor = 0.6 + 0.2 × complexity      # projects only, complexity 1..5; else 1.0
role_factor = {Contributor: 1.0, Lead: 1.3, Architect: 1.5}   # projects only; else 1.0
decay = 0.5 ** (age_months / half_life_months)   # default half-life 24; per-skill override
age_months = months between occurred_on (project: end_date or today if ongoing) and REFERENCE_DATE

total = Σ contribution(e)
score = 100 × (1 − exp(−total / K)),  K = 40
level: 0-19 Beginner, 20-44 Intermediate, 45-69 Advanced, 70-100 Expert
verified = at least one non-self_declared evidence item exists
```

Certifications expiring before the reference date contribute at 50%. Store the full per-evidence `breakdown` (source, id, description, base, factors, decay, contribution) so the UI can show it.

**Required unit tests:** (a) one recent complexity-3 Lead project yields Intermediate; (b) three such projects yield Advanced; (c) self-declared only yields Beginner and `verified=false`; (d) an evidence item 48 months old contributes about 25% of the same item today.

### 6.2 Ranking (`ranking.py`)

```
final = 100 × (0.45·SkillFit + 0.20·DomainFit + 0.15·Recency + 0.10·Availability + 0.10·Verification)
```

- **Required score targets:** must-have skill = 45 (Advanced), nice-to-have = 20 (Intermediate), unless the parsed query specifies `min_level`.
- **SkillFit** = weighted mean over required skills of `min(1, effective_score / target)`. If the employee lacks the skill, `effective_score` = best over related skills of `strength × 0.5 × related_score`. Nice-to-have skills weigh 0.5, must-have 1.0.
- **DomainFit** = `min(1, Σ recency_decay(project) / 2)` over the employee's projects in the requested domain; 1.0 if no domain requested.
- **Recency** = mean over required skills of `0.5 ** (months_since_latest_evidence / 24)`.
- **Availability** = `clamp(1 − utilization, 0, 1)`.
- **Verification** = fraction of required skills with `verified=true`.
- Return the five sub-scores, matched skills, missing skills and the top evidence items per matched skill.

### 6.3 Near-qualified (`near_qualified.py`)
For a required-skills list (with targets and importance 1.0 default):

```
readiness = Σ importance × min(current, target) / Σ importance × target
gaps = skills with current < 0.8 × target (include domain gap if DomainFit < 0.5)
qualified = no gaps
near_qualified = not qualified AND readiness ≥ 0.60 AND len(gaps) ≤ 2
```

Return per-skill gap in score points, level names, readiness, availability and utilization.

### 6.4 Upskilling paths (`upskilling.py`)
For each gap skill build a path from these interventions, choosing greedily until cumulative gain ≥ gap points:

1. **Course** from `course` table matching the skill and the employee's level. Gain = `points_gain`. Weeks = `ceil(hours / learning_hours_per_week)` where `learning_hours_per_week = clamp(40 × (1 − utilization) × 0.15, 2, 6)`.
2. **Stretch assignment** (only if availability ≥ 20%): gain 20 points, 8 weeks.
3. **Mentor:** the top employee with `score ≥ 70` in the skill and utilization < 0.85. Applying a mentor divides weeks by 1.25.

Output per gap skill: ordered steps (type, title, gain, weeks, mentor if any), and total `estimated_weeks`. Overall `time_to_qualified_weeks` = max across gap skills (skills progress in parallel).

### 6.5 Live update
`POST /api/evidence` writes the record, runs extraction (for projects), regenerates evidence, recomputes proficiency for the affected employee only, and returns before/after values plus rank change if a `query_context` is supplied. Target: under 2 seconds.

---

## 7. Extraction (`extraction.py`)
1. Lowercase and tokenize the description; match canonical names and aliases using word-boundary regex, longest match first (so "react native" is not "react").
2. Confidence 0.9 for exact/alias match. Domain detected by domain keyword hits.
3. Unmatched capitalized technology-like tokens go to the LLM fallback (if available) with the list of canonical skills; accept only results that map to an existing skill; confidence 0.6.
4. Write `project_skill` rows. Skills with confidence below 0.5 are ignored.

**Accuracy test:** over the seeded projects, compare extracted skills to `_truth_skills`: precision ≥ 0.85 and recall ≥ 0.80.

---

## 8. API contract (JSON, all under `/api`)

**`POST /search`**
Request: `{ "query": string, "limit": 10, "filters": { "department": string|null, "max_utilization": number|null } }`
Response:
```json
{
  "parsed": {
    "required_skills": [{"skill_id": 1, "name": "React", "min_score": 45, "importance": 1.0}],
    "nice_to_have": [],
    "domain": "fintech",
    "seniority": null,
    "headcount": 1,
    "parser": "llm"
  },
  "results": [{
    "rank": 1,
    "employee": {"id": 7, "name": "Ananya Rao", "role": "Senior Engineer", "department": "Frontend", "utilization": 0.3},
    "score": 87.4,
    "breakdown": {"skill_fit": 0.95, "domain_fit": 0.9, "recency": 0.92, "availability": 0.7, "verification": 1.0},
    "matched_skills": [{"skill_id": 1, "name": "React", "score": 78.2, "level": "Expert", "verified": true, "evidence_count": 3}],
    "missing_skills": [],
    "explanation": "string"
  }],
  "near_qualified": [ /* same shape as /near-qualified items, max 5 */ ],
  "explanation_mode": "llm|template"
}
```

**`GET /employees`** query params `q`, `department`, `limit` → `[{id, name, role, department, level, utilization}]`

**`GET /employees/{id}`** → profile + `skills: [{skill_id, name, category, score, level, verified, breakdown: [ {source_type, source_id, description, occurred_on, base, complexity_factor, role_factor, decay, contribution} ]}]`, `projects`, `certifications`, `trainings`, `self_declared_unverified: [skill names]`.

**`POST /near-qualified`** Request: `{ "required_skills": [{"skill_id":1,"min_score":45}], "domain": "fintech"|null, "max_gaps": 2 }`
Response: `[{ "employee": {...}, "readiness": 0.72, "gaps": [{"skill": "Payments Integration", "current": 12.0, "target": 45, "gap_points": 33, "type": "skill|domain"}], "availability": 0.4, "upskilling": {"paths": [{"skill":"...", "steps":[{"type":"course|stretch|mentor","title":"...","gain":15,"weeks":4,"mentor":{"id":3,"name":"Divya Menon"}|null}], "estimated_weeks": 6}], "time_to_qualified_weeks": 8}}]`

**`POST /evidence`** Request:
```json
{ "employee_id": 12, "type": "project|certification|training",
  "project": {"name": "", "description": "", "domain": "fintech", "complexity": 4, "role": "Lead", "allocation_pct": 50, "start_date": "2026-01-01", "end_date": null},
  "certification": {"certification_id": 3, "issued_on": "2026-08-01"},
  "training": {"course_name": "", "skill_ids": [1], "completed_on": "2026-09-01"},
  "query_context": { /* optional: the `parsed` object from /search */ } }
```
Response: `{ "extracted_skills": [{"skill_id":1,"name":"React","confidence":0.9}], "proficiency_changes": [{"skill":"Payments Integration","before":12.0,"after":34.5,"level_before":"Beginner","level_after":"Intermediate"}], "rank_before": 9, "rank_after": 4 }` (rank fields null when no query_context)

**`GET /graph?employee_id=` or `?skill_id=`** → `{ "nodes":[{"id":"emp_7","type":"employee|skill|project|certification|domain","label":"","data":{}}], "edges":[{"source":"emp_7","target":"proj_3","type":"WORKED_ON|USED|HAS_SKILL|HOLDS|VALIDATES|RELATED_TO|IN_DOMAIN","weight":0.8}] }` (max 150 nodes, 2-hop neighborhood).

**`GET /dashboard/coverage`** → `{ "departments": [...], "categories": [...], "matrix": [[count of employees at Advanced+]], "single_points_of_failure": [{"skill":"","holder":""}], "top_gaps": [{"skill":"","holders":0}] }`

**`GET /skills`** → `[{id, name, category, aliases}]`. **`POST /admin/reseed`** recreates seed data.

**Stretch marketplace:** `GET/POST /openings`, `POST /openings/{id}/interest`, `GET /openings/{id}/matches` (uses the ranking function with the opening's required skills).

Errors: standard FastAPI JSON `{ "detail": "..." }` with proper status codes.

---

## 9. LLM usage (`llm.py`)

### 9.1 Query parsing
System prompt: "You extract structured staffing requirements. Return ONLY valid JSON matching the schema. Map skills to the provided canonical skill list; ignore anything not in it." Provide the canonical skill and domain names in the prompt. Schema: `{required_skills: [names], nice_to_have: [names], domain: name|null, seniority: string|null, headcount: int}`. Validate against the taxonomy; drop unknown names. Temperature 0.

### 9.2 Explanation
Send the computed result for **one candidate** (sub-scores, matched skills with evidence descriptions and dates, missing skills, utilization) and instruct: "Write 2-3 sentences explaining why this person matches. Use ONLY facts in the JSON. Do not invent projects, dates or skills." Temperature 0.2. Batch up to 5 candidates per call for speed (JSON array in, JSON array out).

### 9.3 Cache
Cache every LLM response in `llm_cache` keyed by SHA-256 of (model + prompt). Pre-warm by running the demo queries once.

### 9.4 Fallbacks (mandatory)
- No API key, timeout (8 s) or invalid JSON → **rule-based parser** (taxonomy/alias matching plus domain keywords, "senior/lead" seniority words, digits for headcount) and **template explanation**: "Matches {n}/{m} required skills. {Skill} is {level} ({k} projects, latest {months} months ago). {Domain note}. Currently {utilization}% utilized."
- Set `parser` and `explanation_mode` in the response accordingly.

---

## 10. Frontend requirements

Design: clean, modern, light theme, responsive at 1280px+, consistent components, loading skeletons and friendly error states. Navigation bar: Search, Graph, Dashboard, (Marketplace if built).

1. **Search page (home):** large query input with the demo query as placeholder and 3 clickable example queries. Shows **parsed-query chips** (skills, domain, seniority). Results list with rank, score, availability bar, sub-score bars, matched skills with level badges (Verified checkmark or "Unverified" tag) and the explanation. Clicking a card opens the profile. A second section, "Near-qualified", lists employees with readiness bar, gaps and a "View upskilling path" expandable.
2. **Employee profile:** header, skill list sorted by score with level badges, and an **evidence drawer** per skill showing each evidence item with its contribution and decay ("Project X, 8 months ago, contributes 11.2"). Self-declared-only skills grouped as "Unverified". Button **"Add evidence"** opens a modal (project form / certification / training) that calls `POST /evidence` and then shows a **before/after panel** with skill score changes and the rank change.
3. **Near-qualified detail:** gap breakdown per skill (current vs target bars) and the upskilling path as a step timeline with weeks, mentor name and total time-to-qualified.
4. **Graph page:** Cytoscape view for a selected employee or skill, color-coded by node type, node click shows details, legend, layout `cose`.
5. **Dashboard:** heatmap (departments × skill categories), single points of failure list, top skill gaps chart.
6. **Marketplace (stretch):** openings list, match score and gaps for the selected employee, "Express interest".

Global: a **"Reset demo data"** button (calls `/admin/reseed`) in a footer/settings menu.

---

## 11. Non-functional requirements
- Search (LLM cached or fallback) ≤ 3 s; uncached LLM search ≤ 8 s with fallback on timeout.
- Add-evidence round trip ≤ 2 s.
- Graph endpoint ≤ 1 s and ≤ 150 nodes.
- No secrets in the repo; `.env.example` provided.
- Backend type hints and docstrings on service functions; ruff-clean.
- README with the exact commands to install, seed and run both servers.

---

## 12. Build phases (agent execution order)

| Phase | Work | Done when |
|---|---|---|
| **0. Scaffold** | Repo structure, dependencies, FastAPI hello route, Vite app with proxy, `config.py`, README | Both servers start; `/api/health` visible from frontend |
| **1. Data** | Models, taxonomy JSON, courses JSON, seed generator with planted scenarios, `/skills`, `/employees` | Seed runs; counts match Section 5.2; scenario employees exist |
| **2. Extraction + Proficiency** | Extraction service, evidence generation, proficiency engine, `/employees/{id}` with breakdown | Unit tests 6.1(a-d) and extraction accuracy test pass |
| **3. Search** | Rule-based parser, ranking, `/search` with template explanations | Demo query ranks Ananya first; Sana not in top 5; Vikram below recent experts |
| **4. Near-qualified + Upskilling** | Sections 6.3-6.4, `/near-qualified`, near-qualified block in `/search` | Meera and Karthik appear with correct gaps and paths including Divya as mentor |
| **5. Live update** | `/evidence` with before/after and rank change | Live-update scenario (Section 5.3) passes |
| **6. Frontend core** | Search page, profile with evidence drawer, add-evidence modal with before/after, near-qualified views | Full demo flow works in the browser |
| **7. LLM layer** | Claude parsing and explanation, cache, fallbacks | Works with and without API key; cached demo queries are instant |
| **8. Graph + Dashboard** | `/graph`, `/dashboard/coverage`, both pages | Pages render with real data |
| **9. Polish** | Loading/error states, empty states, styling, reset button, README, `DECISIONS.md` | Acceptance criteria all pass |
| **10. (Stretch) Marketplace** | Openings, interest, matches | Only if Phase 9 is complete |

---

## 13. Acceptance criteria

1. `python -m app.seed.seed` creates 100 employees, 40 projects, about 60 skills and all planted scenarios, reproducibly.
2. Proficiency unit tests (6.1 a-d) pass.
3. Extraction precision ≥ 0.85 and recall ≥ 0.80 on seeded projects.
4. Demo query returns Ananya Rao at rank 1, Rohan Iyer within the top 3, Sana Khan outside the top 5, and Vikram Shah below at least two candidates with recent React and Node.js evidence.
5. Every displayed proficiency level opens an evidence breakdown; self-declared-only skills are labelled "Unverified".
6. Near-qualified results for the demo query include Meera Nair and Karthik Reddy with their expected gaps, an upskilling path each, and a time-to-qualified estimate.
7. Adding the "Wallet Payments Redesign" project for Meera Nair completes in ≤ 2 s and shows a Payments Integration increase and a rank improvement of at least 3 places.
8. The app works with no `ANTHROPIC_API_KEY` (fallback parser and template explanations).
9. Graph page renders a neighborhood for any employee; dashboard heatmap shows real counts.
10. Fresh clone → follow README → app runs without manual fixes.

---

## 14. Demo script (the app must support this end to end)
1. Search the demo query → ranked, explained candidates.
2. Open Ananya's profile → expand React evidence.
3. Show Meera in Near-qualified → gap and upskilling path with mentor and weeks.
4. Add the Wallet Payments Redesign project to Meera → before/after and rank change.
5. Show the graph for Meera and the coverage dashboard.