// CrimeScope — Neo4j Schema Constraints & Indexes
// Applied automatically at startup by driver.py

// ── Uniqueness Constraints ───────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (w:Weapon) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE;

// ── Confidence & Citation Constraints ────────────────────────────────
// All nodes MUST have a confidence score and source citations.
// Enforced at the application layer — Neo4j 5 property existence
// constraints require Enterprise Edition, so we enforce via defaults.
//
// Default values applied by GraphAgent / buffer.py:
//   confidence: 0.0 (range 0.0 - 1.0)
//   sources: []    (list of citation strings)
//   extraction_method: "llm" | "regex_fallback" | "manual"

// ── Performance Indexes ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.job_id);
CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.job_id);
CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.job_id);
CREATE INDEX IF NOT EXISTS FOR (ev:Evidence) ON (ev.job_id);
CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.role);

// ── Confidence-based query indexes ───────────────────────────────────
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.confidence);
CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.confidence);
CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.confidence);
CREATE INDEX IF NOT EXISTS FOR (ev:Evidence) ON (ev.confidence);

// ── Full-text search index (for name lookups) ────────────────────────
// Uncomment if Neo4j Enterprise / AuraDB:
// CREATE FULLTEXT INDEX entity_names IF NOT EXISTS
//   FOR (n:Person|Location|Organization) ON EACH [n.name];
