import { CORE_EVENT_NAMES } from "./coreEventLog";
import { QCP_CORE_PROFILE } from "./coreEvaluation";

export type CoreBindingStatus = "BOUND";

export type CoreBindingRow = {
  item: string;
  binding: string;
  status: CoreBindingStatus;
  rule: string;
};

export const CORE_BINDING_LEDGER: CoreBindingRow[] = [
  {
    item: "Project/Story/Chapter/World/DNA API paths",
    binding: "POST /api/core/action → applyWorkbenchAction(core) → previewCoreAction + applyProjectedAction (control uids CORE-01-*)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Blueprint candidate/version API",
    binding: "CORE-01-ACT-BLUEPRINT-CREATE / BLUEPRINT-VALIDATE / BLUEPRINT-APPROVE (lib/coreActionPreview.ts)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Topic create/confirm/version API",
    binding: "CORE-01-ACT-TOPIC-CREATE → CORE-01-CTL-TOPIC / CORE-01-FLD-TOPIC-SCOPE (topic_scope.confirmed event)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Canonical Script API",
    binding: "CORE-01-BTN-CANONICAL-SCRIPT via buildCanonicalScript + enrichCanonicalScriptProjection (applyAction.ts)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Machine Structured Script schema/service",
    binding: "MSS-1 schema in lib/canonicalViews.ts (structure/machine/views/continuity), output_hash FNV",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Mother/Child/DNA Lock review service/permission",
    binding: "two-step LOCK-REQUEST/APPROVE with evidence precheck in applyAction.ts; approval = reviewer path only (never AI)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Project/Topic/Script/DNA persistence tables",
    binding: "ghsn_core_field_projection (FIELD_TABLE.core), conversation files via persistFindConversationFileByTask",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Event transport/topic names",
    binding: `CORE-01-FLD-EVENT-LOG field ledger, canonical names in CORE_EVENT_NAMES (${CORE_EVENT_NAMES.project_created}, ${CORE_EVENT_NAMES.dna_lock_requested}, …); transport = in-band read model`,
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Idempotency storage/TTL",
    binding: "CORE-01-FLD-IDEMPOTENCY ledger (key ACCEPT:<version>, content-level, cap 50; no TTL — content hash keyed)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Criteria/QA versions",
    binding: `${QCP_CORE_PROFILE} (lib/coreEvaluation.ts, threshold 95, rights_policy hard block)`,
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Rights policy IDs",
    binding: "CORE-01-FLD-NAMING-AUTHORITY = ACPOS_SYSTEM (written at PROJECT-CREATE)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
  {
    item: "Downstream ASSET/VIDEO/EDIT/QA route/workspace IDs",
    binding: "HANDOFF receipt fields CORE-01-FLD-DOWNSTREAM-ASSET/VIDEO/EDIT (workspace materialization owned by consumer systems)",
    status: "BOUND",
    rule: "REQUIRE_EXACT_BINDING",
  },
];

export function coreBindingSummary(): { total: number; bound: number } {
  return { total: CORE_BINDING_LEDGER.length, bound: CORE_BINDING_LEDGER.filter((row) => row.status === "BOUND").length };
}
