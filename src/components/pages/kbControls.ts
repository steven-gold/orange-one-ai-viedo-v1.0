export {
  KB_VISIBLE_CONTROLS,
  KB_CONTROL_ACTIONS,
  KB_VIEWS,
  KB_VIEW_CONTROLS,
  KB_STATE_ERROR_UID,
  KB_STATE_AUDIT_UID,
  KB_STATE_IDEMPOTENCY_UID,
  KB_STATE_SOURCES_UID,
  KB_STATE_RUNS_UID,
  KB_STATE_RESULTS_UID,
  KB_STATE_CITATIONS_UID,
  KB_STATE_BASKET_UID,
  KB_STATE_CANDIDATES_UID,
  KB_STATE_EXPERIENCE_UID,
  KB_STATE_REPLAY_UID,
  KB_STATE_LEARNING_UID,
  KB_STATE_DRAFTS_UID,
  type KbView,
} from "@/server/domain/kb";

import type { TranslationKey } from "@/i18n/catalog";
import type { KbView } from "@/server/domain/kb";

export type KbDrawer = "search" | "citation" | "ingestion" | "replay" | "basket";

export const KB_VIEW_ACTIONS: Record<KbView, readonly string[]> = {
  "KB-01-VIEW-OVERVIEW": ["CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL"],
  "KB-01-VIEW-SOURCE": [
    "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE",
    "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE",
    "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE",
    "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME",
    "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE",
    "CTRL-ADMIN-KB-01-ACT-INGEST-START",
    "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY",
  ],
  "KB-01-VIEW-SEARCH": [
    "CTRL-ADMIN-KB-01-ACT-SEARCH",
    "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN",
    "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD",
    "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE",
    "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE",
  ],
  "KB-01-VIEW-EXPERIENCE": [
    "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN",
    "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE",
    "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE",
    "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP",
  ],
  "KB-01-VIEW-REVIEW": [
    "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE",
    "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE",
    "CTRL-ADMIN-KB-01-ACT-APPROVE",
    "CTRL-ADMIN-KB-01-ACT-RETURN",
    "CTRL-ADMIN-KB-01-ACT-REJECT",
  ],
};

export const KB_PRIMARY_ACTIONS = new Set([
  "CTRL-ADMIN-KB-01-ACT-SEARCH",
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE",
  "CTRL-ADMIN-KB-01-ACT-APPROVE",
]);

export const KB_DANGER_ACTIONS = new Set([
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE",
  "CTRL-ADMIN-KB-01-ACT-REJECT",
]);

export interface KbFormField {
  key: string;
  label: string;
  area?: boolean;
  list?: boolean;
  required?: boolean;
}

// Contract request_schemas: required/optional fields per effectful action.
export const KB_FORM_SCHEMAS: Record<string, KbFormField[]> = {
  "CTRL-ADMIN-KB-01-ACT-SEARCH": [{ key: "query", label: "query", required: true }, { key: "scope", label: "scope", required: true }],
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL": [{ key: "query", label: "query", required: true }, { key: "scope", label: "scope", required: true }],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": [
    { key: "name", label: "name", required: true },
    { key: "source_type", label: "source_type", required: true },
    { key: "scope", label: "scope", required: true },
    { key: "rights", label: "rights", required: true },
    { key: "classification", label: "classification", required: true },
    { key: "collection_method", label: "collection_method", required: true },
    { key: "freshness_policy", label: "freshness_policy", required: true },
    { key: "retention_policy", label: "retention_policy", required: true },
    { key: "collection_config", label: "collection_config (JSON)", area: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": [
    { key: "source_id", label: "source_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "name", label: "name" },
    { key: "scope", label: "scope" },
    { key: "rights", label: "rights" },
    { key: "classification", label: "classification" },
    { key: "freshness_policy", label: "freshness_policy" },
    { key: "retention_policy", label: "retention_policy" },
  ],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE": [
    { key: "source_id", label: "source_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "reason", label: "reason", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME": [
    { key: "source_id", label: "source_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "reason", label: "reason", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE": [
    { key: "source_id", label: "source_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "reason", label: "reason", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": [
    { key: "source_ref", label: "source_ref", required: true },
    { key: "scope", label: "scope", required: true },
    { key: "run_type", label: "run_type (WEB_FETCH/WEB_CRAWL)", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY": [
    { key: "run_id", label: "run_id", required: true },
    { key: "failure_ref", label: "failure_ref", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": [{ key: "citation_id", label: "citation_id", required: true }],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD": [{ key: "ref", label: "ref (result url)", required: true }],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE": [{ key: "ref", label: "ref", required: true }],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": [
    { key: "purpose", label: "purpose", required: true, area: true },
    { key: "scope", label: "scope", required: true },
    { key: "evidence_refs", label: "evidence_refs (comma separated)", list: true, required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": [{ key: "experience_id", label: "experience_id", required: true }],
  "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE": [
    { key: "experience_id", label: "experience_id", required: true },
    { key: "compare_refs", label: "compare_refs (comma separated)", list: true, required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": [
    { key: "experience_refs", label: "experience_refs (comma separated)", list: true, required: true },
    { key: "scope", label: "scope", required: true },
    { key: "pattern", label: "pattern", required: true, area: true },
    { key: "proposed_improvement", label: "proposed_improvement", required: true, area: true },
    { key: "limitations", label: "limitations", area: true, required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": [
    { key: "experience_refs", label: "experience_refs (comma separated)", list: true, required: true },
    { key: "scope", label: "scope", required: true },
    { key: "knowledge_type", label: "knowledge_type", required: true },
    { key: "title_seed", label: "title_seed" },
  ],
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": [
    { key: "knowledge_id", label: "knowledge_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "title", label: "title", required: true },
    { key: "knowledge_type", label: "knowledge_type", required: true },
    { key: "scope", label: "scope", required: true },
    { key: "classification", label: "classification", required: true },
    { key: "summary", label: "summary", area: true },
    { key: "content", label: "content", area: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE": [
    { key: "knowledge_id", label: "knowledge_id", required: true },
    { key: "left_version", label: "left_version", required: true },
    { key: "right_version", label: "right_version", required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-APPROVE": [
    { key: "knowledge_id", label: "knowledge_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "review_rationale", label: "review_rationale", required: true, area: true },
    { key: "mandatory_check_results", label: "mandatory_check_results (JSON)", area: true, required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-RETURN": [
    { key: "knowledge_id", label: "knowledge_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "review_rationale", label: "review_rationale", required: true, area: true },
    { key: "mandatory_check_results", label: "mandatory_check_results (JSON)", area: true, required: true },
  ],
  "CTRL-ADMIN-KB-01-ACT-REJECT": [
    { key: "knowledge_id", label: "knowledge_id", required: true },
    { key: "expected_version", label: "expected_version", required: true },
    { key: "review_rationale", label: "review_rationale", required: true, area: true },
    { key: "mandatory_check_results", label: "mandatory_check_results (JSON)", area: true, required: true },
  ],
};

export const KB_ACTION_LABELS: Record<string, TranslationKey> = {
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL": "kb.act-search",
  "CTRL-ADMIN-KB-01-ACT-SEARCH": "kb.act-search",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": "kb.act-source-create",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": "kb.act-source-save",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE": "kb.act-source-pause",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME": "kb.act-source-resume",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE": "kb.act-source-retire",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": "kb.act-ingest-start",
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY": "kb.act-ingest-retry",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": "kb.act-citation-open",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD": "kb.act-context-add",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE": "kb.act-context-remove",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": "kb.act-context-create",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": "kb.act-replay-open",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE": "kb.act-replay-compare",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": "kb.act-learning-create",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": "kb.act-draft-from-exp",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": "kb.act-draft-save",
  "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE": "kb.act-version-compare",
  "CTRL-ADMIN-KB-01-ACT-APPROVE": "kb.act-approve",
  "CTRL-ADMIN-KB-01-ACT-RETURN": "kb.act-return",
  "CTRL-ADMIN-KB-01-ACT-REJECT": "kb.act-reject",
};
