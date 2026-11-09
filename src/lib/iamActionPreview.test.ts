import { previewIamAction, readWorkbench, buildAssignmentPlan, l1ByKey } from "./iamActionPreview";
import { IAM_VISIBLE_CONTROLS } from "../server/domain/iam";
import { IAM_BACK_L1_CATALOG, IAM_FRONT_L1_CATALOG, type IamAccountRow } from "./iamState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function json<T>(text: string | null, fallback: T): T {
  const trimmed = (text ?? "").trim();
  if (!trimmed) return fallback;
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return fallback;
  }
}

function store(seed: Record<string, string> = {}): {
  current: (uid: string) => string | null;
  apply: (controlUid: string, actionUid: string, nextValue?: string) => Record<string, string>;
} {
  const values = new Map<string, string>(Object.entries(seed));
  const current = (uid: string) => values.get(uid) ?? null;
  const apply = (controlUid: string, actionUid: string, nextValue?: string) => {
    const patch = previewIamAction(controlUid, actionUid, current, nextValue);
    for (const [uid, value] of Object.entries(patch)) values.set(uid, value);
    return patch;
  };
  return { current, apply };
}

const ACCOUNT: IamAccountRow = {
  accountUid: "ACC-T1",
  email: "user@orange-one.local",
  status: "ACTIVE",
  sessions: 1,
  lastSeenAt: "2026-11-09T00:00:00.000Z",
  frontendL1: ["iam.front-01"],
  backendL1: [],
};

{
  // Word §29 PASS baseline + Batch closure: the exact 14-control denominator.
  assert(IAM_VISIBLE_CONTROLS.length === 14, "IAM stays at 14 visible controls");
  assert(IAM_VISIBLE_CONTROLS.includes("IAM-01-BTN-COMPLETE"), "complete remains a visible control");
  assert(IAM_FRONT_L1_CATALOG.length === 9, "exactly 9 frontend L1 choices");
  assert(IAM_BACK_L1_CATALOG.length === 9, "exactly 9 backend L1 choices");
  assert(IAM_FRONT_L1_CATALOG[0].key === "iam.front-01" && IAM_FRONT_L1_CATALOG[0].pageUid === "workspace:WB-01", "frontend L1 order locked (word Table 13)");
  assert(IAM_BACK_L1_CATALOG[0].key === "iam.back-01" && IAM_BACK_L1_CATALOG[0].pageUid === "admin:SYS-01", "backend L1 order locked (word Table 13)");
  assert(IAM_BACK_L1_CATALOG[1].pageUid === "admin:IAM-01" && IAM_BACK_L1_CATALOG[1].permission === "iam.user.configure", "backend IAM L1 binds its exact permission");
  // No wildcard anywhere in the materialization catalog.
  for (const choice of [...IAM_FRONT_L1_CATALOG, ...IAM_BACK_L1_CATALOG]) {
    assert(!choice.permission.includes("*"), `no wildcard in ${choice.permission}`);
    assert(choice.permissionTable.startsWith("ghsn_account_"), `${choice.permissionTable} is a governed table`);
  }
}

{
  // Create flow: draft context, preset suggestion, select-all, save, validate.
  const s = store();
  s.apply("IAM-01-BTN-ADD", "IAM-01-ACT-OPEN-CREATE");
  const draft = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(draft.mode === "CREATE" && draft.correlationId, "open create builds a draft context with correlation");

  const presetFail = s.apply("IAM-01-SEL-DEPT-PRESET", "IAM-01-ACT-PRESET-APPLY-TO-DRAFT", JSON.stringify({ presetId: "missing" }));
  assert(json<{code: string}>(presetFail["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_PRESET_UNRESOLVED", "unknown preset fails closed without guessing");

  s.apply("IAM-01-SEL-DEPT-PRESET", "IAM-01-ACT-PRESET-APPLY-TO-DRAFT", JSON.stringify({ presetId: "ops-front" }));
  const preDraft = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(JSON.stringify(preDraft.frontL1) === JSON.stringify(["iam.front-01", "iam.front-02", "iam.front-03"]), "preset prefills the draft only");

  s.apply("IAM-01-CHK-FRONT-ALL", "IAM-01-ACT-FRONT-ALL-DRAFT");
  assert(json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 }).frontL1.length === 9, "front all selects all nine draft choices");
  s.apply("IAM-01-CHK-FRONT-ALL", "IAM-01-ACT-FRONT-ALL-DRAFT");
  assert(json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 }).frontL1.length === 0, "front all toggles off");
  s.apply("IAM-01-CHK-FRONT-ALL", "IAM-01-ACT-FRONT-ALL-DRAFT");

  s.apply("IAM-01-GRP-FRONT-L1", "IAM-01-ACT-L1-DRAFT-SET", JSON.stringify({ side: "FRONT", key: "iam.front-01", selected: false }));
  const afterUnset = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(afterUnset.frontL1.length === 8, "single L1 toggle unsets");
  const unknown = s.apply("IAM-01-GRP-FRONT-L1", "IAM-01-ACT-L1-DRAFT-SET", JSON.stringify({ side: "FRONT", key: "iam.admin:*", selected: true }));
  assert(json<{code: string}>(unknown["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_L1_UNRESOLVED", "unknown L1 key fails closed");

  s.apply("IAM-01-BTN-SAVE-DRAFT", "IAM-01-ACT-SAVE-DRAFT");
  const saved = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(saved.savedAt && saved.version === 1, "save draft stamps correlation without inflating version");
  s.apply("IAM-01-BTN-SAVE-DRAFT", "IAM-01-ACT-SAVE-DRAFT");
  assert(json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 }).version === 2, "second save bumps the draft version");

  const noBasic = s.apply("IAM-01-BTN-VALIDATE", "IAM-01-ACT-VALIDATE-DRAFT");
  assert(json<{code: string}>(noBasic["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_BASIC_DATA_REQUIRED", "validate requires basic data");
  s.apply("IAM-01-CTL-BASIC-DATA", "IAM-01-ACT-BASIC-DATA-EDIT", JSON.stringify({ displayName: "新帳號", email: "new@orange-one.local" }));
  s.apply("IAM-01-BTN-VALIDATE", "IAM-01-ACT-VALIDATE-DRAFT");
  const validated = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(validated.version === 3, "validated draft bumps version");
}

{
  // Preview + complete gate with a real account (edit mode).
  const s = store({
    "IAM-01-STATE-ACCOUNTS": JSON.stringify([ACCOUNT]),
    "IAM-01-STATE-MODE": "EDIT",
  });
  s.apply("IAM-01-BTN-EDIT", "IAM-01-ACT-OPEN-EDIT", JSON.stringify({ accountId: "ACC-T1" }));
  const draft = json<{ frontL1: string[]; mode: string; accountId: string; version: number; correlationId?: string; savedAt?: string; basicData?: { displayName: string } }>(s.current("IAM-01-STATE-DRAFT"), { frontL1: [], mode: "", accountId: "", version: 0 });
  assert(draft.mode === "EDIT" && draft.accountId === "ACC-T1", "open edit binds the exact account");
  assert(draft.frontL1.includes("iam.front-01"), "edit draft carries current assignments");

  s.apply("IAM-01-GRP-BACK-L1", "IAM-01-ACT-L1-DRAFT-SET", JSON.stringify({ side: "BACK", key: "iam.back-01", selected: true }));
  s.apply("IAM-01-GRP-FRONT-L1", "IAM-01-ACT-L1-DRAFT-SET", JSON.stringify({ side: "FRONT", key: "iam.front-01", selected: false }));
  s.apply("IAM-01-CTL-BASIC-DATA", "IAM-01-ACT-BASIC-DATA-EDIT", JSON.stringify({ displayName: "user" }));
  s.apply("IAM-01-BTN-VALIDATE", "IAM-01-ACT-VALIDATE-DRAFT");

  const noPreview = s.apply("IAM-01-BTN-COMPLETE", "IAM-01-ACT-COMPLETE", JSON.stringify({ confirm: true }));
  assert(json<{code: string}>(noPreview["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_PREVIEW_REQUIRED", "complete requires a fresh preview");

  s.apply("IAM-01-BTN-PREVIEW", "IAM-01-ACT-PREVIEW");
  const preview = json<{added: number; removed: number; blocked: number; deltas: Array<{kind: string; permission: string; permissionTable: string}>}>(s.current("IAM-01-STATE-PREVIEW"), { added: 0, removed: 0, blocked: 0, deltas: [] });
  assert(preview.added === 1 && preview.removed === 1, "preview diffs added and removed exactly");
  assert(preview.blocked === 0, "preview has no blockers for known L1 keys");
  const addedRow = preview.deltas.find((row) => row.kind === "ADDED") as { kind: string; permission: string; permissionTable: string };
  const removedRow = preview.deltas.find((row) => row.kind === "REMOVED") as { kind: string; permission: string; permissionTable: string };
  assert(addedRow.permission === "system.change.propose" && addedRow.permissionTable === "ghsn_account_sys_permission", "added row materializes the exact permission");
  assert(removedRow.permission === "workspace.dashboard.view", "removed row names the exact permission");

  const noConfirm = s.apply("IAM-01-BTN-COMPLETE", "IAM-01-ACT-COMPLETE", JSON.stringify({}));
  assert(json<{code: string}>(noConfirm["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_CONFIRM_REQUIRED", "complete requires explicit confirmation");

  const complete = s.apply("IAM-01-BTN-COMPLETE", "IAM-01-ACT-COMPLETE", JSON.stringify({ confirm: true }));
  const plan = json<unknown[]>(complete["IAM-01-STATE-PLAN"], []);
  assert(Array.isArray(plan) && plan.length === 2, "plan carries exactly the changed assignments");
  const assign = plan.find((row) => (row as { mode?: string }).mode === "ASSIGN") as { mode: string; permission: string; accountUid: string };
  const revoke = plan.find((row) => (row as { mode?: string }).mode === "REVOKE") as { mode: string; permission: string; accountUid: string };
  assert(assign.permission === "system.change.propose" && assign.accountUid === "ACC-T1", "assign plan row is exact");
  assert(revoke.permission === "workspace.dashboard.view", "revoke plan row is exact");
  // Silent future grant: unchanged rows never enter the plan.
  assert(!plan.some((row) => (row as { mode?: string }).mode === "UNCHANGED"), "no silent grant of unchanged rows");
}

{
  // Stale preview + validated-but-unpreviewed drafts are refused (word
  // GATE-COMPLETE: stale preview must be rejected or refreshed).
  const s = store({
    "IAM-01-STATE-ACCOUNTS": JSON.stringify([ACCOUNT]),
    "IAM-01-STATE-MODE": "EDIT",
  });
  s.apply("IAM-01-BTN-EDIT", "IAM-01-ACT-OPEN-EDIT", JSON.stringify({ accountId: "ACC-T1" }));
  s.apply("IAM-01-CTL-BASIC-DATA", "IAM-01-ACT-BASIC-DATA-EDIT", JSON.stringify({ displayName: "user" }));
  s.apply("IAM-01-GRP-FRONT-L1", "IAM-01-ACT-L1-DRAFT-SET", JSON.stringify({ side: "FRONT", key: "iam.front-02", selected: true }));
  s.apply("IAM-01-BTN-PREVIEW", "IAM-01-ACT-PREVIEW");
  // VALIDATE nulls the preview and bumps the version: COMPLETE sees no fresh
  // preview at all (fail-closed), never applies against a stale one.
  s.apply("IAM-01-BTN-VALIDATE", "IAM-01-ACT-VALIDATE-DRAFT");
  const stale = s.apply("IAM-01-BTN-COMPLETE", "IAM-01-ACT-COMPLETE", JSON.stringify({ confirm: true }));
  assert(json<{code: string}>(stale["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_PREVIEW_REQUIRED", "validated-but-unpreviewed draft cannot complete");
  assert(!stale["IAM-01-STATE-PLAN"], "no materialization plan without a fresh preview");

  // Seeded drift preview (defensive path): COMPLETE refuses via STALE.
  const s2 = store({
    "IAM-01-STATE-ACCOUNTS": JSON.stringify([ACCOUNT]),
    "IAM-01-STATE-MODE": "EDIT",
    "IAM-01-STATE-DRAFT": JSON.stringify({
      mode: "EDIT",
      accountId: "ACC-T1",
      basicData: { displayName: "user", email: "user@orange-one.local", department: "" },
      frontL1: ["iam.front-01"],
      backL1: [],
      correlationId: "COR-SEED",
      savedAt: "",
      version: 2,
    }),
    "IAM-01-STATE-PREVIEW": JSON.stringify({
      accountId: "ACC-T1",
      mode: "EDIT",
      deltas: [],
      added: 0,
      removed: 0,
      unchanged: 1,
      blocked: 0,
      blockers: [],
      stamp: "PVW-seed",
      draftVersion: 1,
      expectedVersion: 1,
    }),
  });
  const drift = s2.apply("IAM-01-BTN-COMPLETE", "IAM-01-ACT-COMPLETE", JSON.stringify({ confirm: true }));
  assert(json<{code: string}>(drift["IAM-01-STATE-ERROR"], { code: "" }).code === "IAM_PREVIEW_STALE", "seeded stale preview is rejected, never applied");
  assert(!drift["IAM-01-STATE-PLAN"], "stale preview never materializes a plan");
}

{
  // buildAssignmentPlan blocks unresolved keys instead of guessing.
  const plan = buildAssignmentPlan(
    {
      mode: "EDIT",
      accountId: "ACC-T1",
      basicData: { displayName: "u", email: "u", department: "" },
      frontL1: ["iam.front-01", "iam.not-real"],
      backL1: [],
      correlationId: "COR-X",
      savedAt: "",
      version: 1,
    },
    [ACCOUNT],
  );
  assert(plan.blockers.includes("IAM_L1_UNRESOLVED:iam.not-real"), "unresolved L1 becomes a blocker");
  assert(plan.deltas.every((row) => row.kind !== "REMOVED" || row.permission), "removal rows always carry an exact permission");
  assert(l1ByKey("iam.admin:*") === null, "wildcard keys never resolve");
}

{
  // Search + audit-open stay page-gated reads without side effects.
  const s = store();
  s.apply("IAM-01-CTL-SEARCH", "IAM-01-ACT-SEARCH", JSON.stringify({ query: "user@orange-one.local" }));
  assert(s.current("IAM-01-STATE-QUERY") === "user@orange-one.local", "search stores the query");
  s.apply("IAM-01-BTN-AUDIT", "IAM-01-ACT-AUDIT-OPEN");
  const wb = readWorkbench(s.current);
  assert(wb.error === null, "audit open does not invent errors");
}
