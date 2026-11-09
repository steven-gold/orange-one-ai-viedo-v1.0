import {
  IAM_BACK_L1_CATALOG,
  IAM_FRONT_L1_CATALOG,
  IAM_L1_CATALOG,
  IAM_DEPT_PRESETS,
  type IamAccountRow,
  type IamAssignmentDelta,
  type IamDraft,
  type IamErrorState,
  type IamL1Choice,
  type IamPreview,
  type IamSide,
  type IamWorkbench,
} from "./iamState";

const nowIso = () => new Date().toISOString();
const newUid = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 8)}-${Math.random().toString(36).slice(2, 8)}`;
const usable = (value: unknown) => (typeof value === "string" && value.trim().length > 0 ? value.trim() : "");

function fail(workbench: IamWorkbench, code: string, patch?: Partial<IamWorkbench>): IamWorkbench {
  return { ...workbench, error: { code, at: nowIso() }, ...patch };
}

function clearError(workbench: IamWorkbench): IamWorkbench {
  return { ...workbench, error: null };
}

export function l1ByKey(key: string): IamL1Choice | null {
  return [...IAM_FRONT_L1_CATALOG, ...IAM_BACK_L1_CATALOG].find((item) => item.key === key) ?? null;
}

export function draftL1IsValid(draft: IamDraft | null): boolean {
  if (!draft) return false;
  return draft.frontL1.length + draft.backL1.length > 0;
}

// Department presets are DRAFT suggestions only (word Table 14): they never
// grant authorization on their own and never apply retroactively.
export function presetById(presetId: string) {
  return IAM_DEPT_PRESETS.find((item) => item.presetId === presetId) ?? null;
}

// Word Table 20: GATE-DRAFT requires manage mode plus a valid draft context.
function draftGateOk(workbench: IamWorkbench): boolean {
  return Boolean(workbench.draft) && (workbench.mode === "CREATE" || workbench.mode === "EDIT");
}

// Word §15 step 2-4: expand each selected L1 into its currently registered
// permission row, then diff against the account's current explicit
// assignments. Unknown L1 keys are BLOCKED, never guessed (word Table 21).
export function buildAssignmentPlan(
  draft: IamDraft,
  accounts: IamAccountRow[],
): { deltas: IamAssignmentDelta[]; blockers: string[] } {
  const account = accounts.find((item) => item.accountUid === draft.accountId);
  const current = new Set<string>([...(account?.frontendL1 ?? []), ...(account?.backendL1 ?? [])]);
  const deltas: IamAssignmentDelta[] = [];
  const blockers: string[] = [];
  for (const side of ["FRONT", "BACK"] as IamSide[]) {
    const selected = side === "FRONT" ? draft.frontL1 : draft.backL1;
    for (const key of selected) {
      const choice = l1ByKey(key);
      if (!choice) {
        blockers.push(`IAM_L1_UNRESOLVED:${key}`);
        continue;
      }
      const exists = current.has(key);
      deltas.push({
        side,
        key,
        pageUid: choice.pageUid,
        permission: choice.permission,
        permissionTable: choice.permissionTable,
        kind: exists ? "UNCHANGED" : "ADDED",
      });
    }
    if (account) {
      const retainedKeys = side === "FRONT" ? account.frontendL1 : account.backendL1;
      for (const key of retainedKeys) {
        const stillSelected = selected.includes(key);
        if (!stillSelected) {
          const choice = l1ByKey(key);
          if (choice) {
            deltas.push({
              side,
              key,
              pageUid: choice.pageUid,
              permission: choice.permission,
              permissionTable: choice.permissionTable,
              kind: "REMOVED",
            });
          } else {
            blockers.push(`IAM_L1_UNRESOLVED:${key}`);
          }
        }
      }
    }
  }
  return { deltas, blockers };
}

export function buildPreview(draft: IamDraft, accounts: IamAccountRow[]): IamPreview {
  const { deltas, blockers } = buildAssignmentPlan(draft, accounts);
  const added = deltas.filter((item) => item.kind === "ADDED").length;
  const removed = deltas.filter((item) => item.kind === "REMOVED").length;
  const unchanged = deltas.filter((item) => item.kind === "UNCHANGED").length;
  return {
    accountId: draft.accountId,
    mode: draft.mode,
    deltas,
    added,
    removed,
    unchanged,
    blocked: blockers.length,
    blockers,
    stamp: newUid("PVW"),
    draftVersion: draft.version,
    expectedVersion: draft.version,
  };
}

// Word Table 19 state machine + Table 20 gates. Actions operate on a pure
// workbench snapshot; COMPLETE returns a materialization plan the server
// runtime executes against the governed permission tables.
export type IamActionUid = string;

export function previewIamAction(
  controlUid: string,
  actionUid: IamActionUid,
  read: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const workbench = readWorkbench(read);
  const payload = parsePayload(nextValue);
  let next: IamWorkbench;

  if (actionUid === "IAM-01-ACT-SEARCH") {
    next = clearError({ ...workbench, query: usable(payload.query) });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-OPEN-CREATE") {
    next = clearError({
      ...workbench,
      mode: "CREATE",
      draft: {
        mode: "CREATE",
        accountId: "",
        basicData: { displayName: "", email: "", department: "" },
        frontL1: [],
        backL1: [],
        correlationId: newUid("COR"),
        savedAt: "",
        version: 1,
      },
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-OPEN-EDIT") {
    const accountId = usable(payload.accountId);
    const account = workbench.accounts.find((item) => item.accountUid === accountId);
    if (!account) return writeWorkbench(fail(workbench, "IAM_ACCOUNT_REQUIRED"));
    next = clearError({
      ...workbench,
      mode: "EDIT",
      draft: {
        mode: "EDIT",
        accountId: account.accountUid,
        basicData: { displayName: account.email, email: account.email, department: "" },
        frontL1: [...account.frontendL1],
        backL1: [...account.backendL1],
        correlationId: newUid("COR"),
        savedAt: "",
        version: 1,
      },
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-BASIC-DATA-EDIT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    const displayName = usable(payload.displayName);
    const email = usable(payload.email);
    const department = usable(payload.department);
    next = clearError({
      ...workbench,
      draft: {
        ...draft,
        basicData: {
          displayName: displayName || draft.basicData.displayName,
          email: email || draft.basicData.email,
          department: department || draft.basicData.department,
        },
      },
      preview: null,
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-PRESET-APPLY-TO-DRAFT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const presetId = usable(payload.presetId);
    const preset = presetById(presetId);
    // Word Table 14: a missing/unresolvable preset renders "no preset / manual
    // configuration" — it must never guess department permissions.
    if (!preset) return writeWorkbench(fail(workbench, "IAM_PRESET_UNRESOLVED"));
    const draft = workbench.draft!;
    next = clearError({
      ...workbench,
      draft: preset.side === "FRONT"
        ? { ...draft, frontL1: [...preset.keys] }
        : { ...draft, backL1: [...preset.keys] },
      preview: null,
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-FRONT-ALL-DRAFT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    const all = IAM_FRONT_L1_CATALOG.map((item) => item.key);
    const turnOff = draft.frontL1.length === all.length;
    next = clearError({ ...workbench, draft: { ...draft, frontL1: turnOff ? [] : all }, preview: null });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-BACK-ALL-DRAFT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    const all = IAM_BACK_L1_CATALOG.map((item) => item.key);
    const turnOff = draft.backL1.length === all.length;
    next = clearError({ ...workbench, draft: { ...draft, backL1: turnOff ? [] : all }, preview: null });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-L1-DRAFT-SET") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const side = usable(payload.side) as IamSide;
    const key = usable(payload.key);
    const selected = payload.selected !== false;
    const choice = l1ByKey(key);
    if (side !== "FRONT" && side !== "BACK") return writeWorkbench(fail(workbench, "IAM_L1_SIDE_INVALID"));
    if (!choice) return writeWorkbench(fail(workbench, "IAM_L1_UNRESOLVED"));
    const draft = workbench.draft!;
    const list = side === "FRONT" ? [...draft.frontL1] : [...draft.backL1];
    const nextList = selected ? (list.includes(key) ? list : [...list, key]) : list.filter((item) => item !== key);
    next = clearError({
      ...workbench,
      draft: side === "FRONT" ? { ...draft, frontL1: nextList } : { ...draft, backL1: nextList },
      preview: null,
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-SAVE-DRAFT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    next = clearError({
      ...workbench,
      draft: { ...draft, savedAt: nowIso(), version: draft.version + (draft.savedAt ? 1 : 0) },
    });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-VALIDATE-DRAFT") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    // Word Table 12: basic data follows the registered schema; an L1 draft
    // needs an intentional selection before preview.
    if (!draft.basicData.displayName) return writeWorkbench(fail(workbench, "IAM_BASIC_DATA_REQUIRED"));
    if (!draftL1IsValid(draft)) return writeWorkbench(fail(workbench, "IAM_L1_SELECTION_REQUIRED"));
    const unresolved = [...draft.frontL1, ...draft.backL1].filter((key) => !l1ByKey(key));
    if (unresolved.length) return writeWorkbench(fail(workbench, `IAM_L1_UNRESOLVED:${unresolved[0]}`));
    next = clearError({ ...workbench, draft: { ...draft, version: draft.version + 1 }, preview: null });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-PREVIEW") {
    if (!draftGateOk(workbench)) return writeWorkbench(fail(workbench, "IAM_DRAFT_REQUIRED"));
    const draft = workbench.draft!;
    if (!draftL1IsValid(draft)) return writeWorkbench(fail(workbench, "IAM_L1_SELECTION_REQUIRED"));
    const preview = buildPreview(draft, workbench.accounts);
    next = clearError({ ...workbench, preview });
    return writeWorkbench(next);
  }

  if (actionUid === "IAM-01-ACT-COMPLETE") {
    // GATE-COMPLETE (word Table 20): fresh preview + no blocker + expected
    // version + explicit confirmation + audit. Partial failures never claim
    // COMPLETE (word ACC-13); the server runtime executes the plan.
    const preview = workbench.preview;
    if (!draftGateOk(workbench) || !preview) return writeWorkbench(fail(workbench, "IAM_PREVIEW_REQUIRED"));
    const draft = workbench.draft!;
    if (preview.accountId !== draft.accountId || preview.draftVersion !== draft.version) {
      return writeWorkbench(fail(workbench, "IAM_PREVIEW_STALE"));
    }
    if (preview.blocked > 0) return writeWorkbench(fail(workbench, "IAM_PREVIEW_BLOCKED"));
    if (payload.confirm !== true) return writeWorkbench(fail(workbench, "IAM_CONFIRM_REQUIRED"));
    const plan = preview.deltas
      .filter((item) => item.kind !== "UNCHANGED")
      .map((item) => ({
        accountUid: draft.accountId,
        permission: item.permission,
        permissionTable: item.permissionTable,
        mode: item.kind === "ADDED" ? "ASSIGN" : "REVOKE",
      }));
    next = clearError({
      ...workbench,
      preview: null,
      apply: {
        accountId: draft.accountId,
        status: "PARTIAL",
        applied: [],
        failed: [],
        correlationId: draft.correlationId,
        stamp: preview.stamp,
        auditEventUid: "",
      },
    });
    const output = writeWorkbench(next);
    output["IAM-01-STATE-PLAN"] = JSON.stringify(plan);
    output["IAM-01-STATE-PLAN-STAMP"] = preview.stamp;
    return output;
  }

  if (actionUid === "IAM-01-ACT-AUDIT-OPEN") {
    next = clearError(workbench);
    return writeWorkbench(next);
  }

  return writeWorkbench(workbench);
}

function parsePayload(nextValue?: string): Record<string, unknown> {
  if (!nextValue) return {};
  try {
    const parsed = JSON.parse(nextValue);
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export function readWorkbench(read: (uid: string) => string | null): IamWorkbench {
  const parse = <T,>(uid: string, fallback: T): T => {
    const text = (read(uid) ?? "").trim();
    if (!text) return fallback;
    try {
      return JSON.parse(text) as T;
    } catch {
      return fallback;
    }
  };
  return {
    accounts: parse("IAM-01-STATE-ACCOUNTS", [] as IamAccountRow[]),
    draft: parse<IamDraft | null>("IAM-01-STATE-DRAFT", null),
    preview: parse<IamPreview | null>("IAM-01-STATE-PREVIEW", null),
    apply: parse("IAM-01-STATE-APPLY", null),
    error: parse<IamErrorState | null>("IAM-01-STATE-ERROR", null),
    query: (read("IAM-01-STATE-QUERY") ?? "").trim(),
    mode: (read("IAM-01-STATE-MODE") ?? "LIST") as IamWorkbench["mode"],
    audit: parse("IAM-01-STATE-AUDIT", [] as string[]),
  };
}

function writeWorkbench(workbench: IamWorkbench): Record<string, string> {
  const output: Record<string, string> = {};
  output["IAM-01-STATE-ACCOUNTS"] = JSON.stringify(workbench.accounts);
  output["IAM-01-STATE-DRAFT"] = workbench.draft ? JSON.stringify(workbench.draft) : "";
  output["IAM-01-STATE-PREVIEW"] = workbench.preview ? JSON.stringify(workbench.preview) : "";
  output["IAM-01-STATE-APPLY"] = workbench.apply ? JSON.stringify(workbench.apply) : "";
  output["IAM-01-STATE-ERROR"] = workbench.error ? JSON.stringify(workbench.error) : "";
  output["IAM-01-STATE-QUERY"] = workbench.query;
  output["IAM-01-STATE-MODE"] = workbench.mode;
  output["IAM-01-STATE-AUDIT"] = JSON.stringify(workbench.audit);
  return output;
}
