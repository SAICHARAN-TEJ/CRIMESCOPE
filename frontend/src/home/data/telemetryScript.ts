/**
 * Live case telemetry script lines.
 * Strictly adheres to real event vocabulary (STAGE_UPDATE, ACTIVITY, DECOMP_UPDATE, AGENT_WAITING).
 */
export const heroTelemetryLines: string[] = [
  '02:14:07 STAGE_UPDATE connect → COMPLETED · 13 items',
  '02:14:09 ACTIVITY graph: Queued relationship: LOCATED_AT',
  '02:14:11 ACTIVITY entity: Found candidate person: P-018',
  '02:14:15 STAGE_UPDATE verify → SKIPPED · Phase 5',
  '02:14:16 ACTIVITY pipeline: Report ready',
  '02:14:18 DECOMP_UPDATE witness_report.pdf: text 4/4 done',
  '02:14:21 AGENT_WAITING entity: waiting for extraction workers',
  '02:14:24 STAGE_UPDATE challenge → ACTIVE · 2 personas',
]
