export const INFO_ACTION_UIDS=[
  "INFO-01-ACT-NOOP",
  "INFO-01-ACT-FILTER",
  "INFO-01-ACT-SOURCE-SELECT",
  "INFO-01-ACT-ALERT-SELECT",
  "INFO-01-ACT-FACTPACK-SELECT",
  "INFO-01-ACT-FACT-TYPE",
  "INFO-01-ACT-EVIDENCE-SELECT",
  "INFO-01-ACT-RESEARCH-SELECT",
  "INFO-01-ACT-CANDIDATE-SELECT",
  "INFO-01-ACT-CITATION-OPEN",
  "INFO-01-ACT-REFRESH",
  "INFO-01-ACT-SEARCH",
  "INFO-01-ACT-PROJECTION-READ",
  "INFO-01-ACT-EXPORT",
  "INFO-01-ACT-ADOPT-CONTEXT",
  "INFO-01-ACT-CANDIDATE-DECIDE",
  "INFO-01-ACT-AUDIT-OPEN",
]as const;
export type InfoActionUid=typeof INFO_ACTION_UIDS[number];
export const INFO_ERROR_UIDS=[
  "INFO-01-ERR-CONTEXT-001",
  "INFO-01-ERR-SOURCE-001",
  "INFO-01-ERR-FRESHNESS-001",
  "INFO-01-ERR-FACTPACK-001",
  "INFO-01-ERR-FACT-001",
  "INFO-01-ERR-EVIDENCE-001",
  "INFO-01-ERR-RESEARCH-001",
  "INFO-01-ERR-SEARCH-001",
  "INFO-01-ERR-EXPORT-001",
  "INFO-01-ERR-CANDIDATE-001",
  "INFO-01-ERR-PERM-001",
  "INFO-01-ERR-UNDEFINED-001",
]as const;
export type InfoErrorUid=typeof INFO_ERROR_UIDS[number];
export const INFO_PORT_UIDS=["INFO-01-PORT-PROJECTION","INFO-01-PORT-REFRESH","INFO-01-PORT-SEARCH","INFO-01-PORT-EXPORT","INFO-01-PORT-CONTEXT-ADOPT","INFO-01-PORT-CANDIDATE-DECIDE"]as const;
export const INFO_PORT_COUNT=INFO_PORT_UIDS.length;
export const INFO_EXPECTED_ACTION_COUNT=INFO_ACTION_UIDS.length;
export const INFO_EXPECTED_ERROR_COUNT=INFO_ERROR_UIDS.length;
export const INFO_EXPECTED_CONTROL_COUNT=66;
export const INFO_PORTS={projection:{operation:"getUiProjection",method:"GET",path:"/v1/ui-projections/{pageUid}"},refresh:{operation:"refreshProjection",method:"POST",path:"/v1/projections/refresh"},search:{operation:"searchProjection",method:"POST",path:"/v1/search"},export:{operation:"exportProjection",method:"POST",path:"/v1/exports"},adopt:{operation:"adoptContextCandidate",method:"POST",path:"/v1/context-candidates/{id}/adopt"},decide:{operation:"decideCandidate",method:"POST",path:"/v1/candidates/{id}/decision"}}as const;
