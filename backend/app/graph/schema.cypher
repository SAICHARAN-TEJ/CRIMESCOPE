// CrimeScope — Neo4j Schema Constraints & Indexes
// Applied automatically at startup by driver.py

// ── Uniqueness Constraints ───────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;

// ── Performance Indexes ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.job_id);
CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.job_id);
CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.job_id);
CREATE INDEX IF NOT EXISTS FOR (ev:Evidence) ON (ev.job_id);
CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.role);
