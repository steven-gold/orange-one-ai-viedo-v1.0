import { configureCoreCreationPermissionAdapter } from "@/domain/core/coreCreationPermissionAdapter";
import { configureCoreDraftFormAdapter } from "@/domain/core/coreDraftFormAdapter";
import { configureCoreConversationPayloadAdapter } from "@/domain/core/coreConversationPayloadAdapter";
import { configureCoreCandidatePayloadAdapter } from "@/domain/core/coreCandidatePayloadAdapter";
import { configureCoreLockCommandPayloadAdapter } from "@/domain/core/coreLockCommandPayloadAdapter";
import { configureCoreComposerResourceAdapter } from "@/domain/core/coreComposerResourceAdapter";
import { configureIamClientCommandAdapter, readIamProjection } from "@/domain/iam/iamClientPort";
import { configureDbClientRuntime, normalizeDbProjection } from "@/domain/database/dbClientPort";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureInfoCommandPayloadBuilder } from "@/domain/info/infoCommandPort";
import { configureStrategyRequestBuilder } from "@/domain/strategy/strategyCommandPort";
import { configureStrategyAdminCommandAdapter } from "@/domain/strategyAdmin/strategyAdminRuntimePort";
import { configureDevCommandAdapter } from "@/domain/dev/devCommandPort";
import { readDevProjection } from "@/domain/dev/devProjectionPort";
import { DEV_CONTROL_BINDINGS, type DevControlUid } from "@/domain/dev/devControlBindings";

let bound = false;

function rec(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function openDraftDialog(kind: "PROJECT" | "TOPIC"): Promise<{ ok: true; payload: Record<string, unknown> } | { ok: false; reason_code: string }> {
  if (typeof document === "undefined") {
    return Promise.resolve({ ok: false, reason_code: "DRAFT_FORM_WINDOW_UNAVAILABLE" });
  }
  return new Promise((resolve) => {
    const existing = document.getElementById("acpos-core-draft-dialog");
    existing?.remove();
    const dialog = document.createElement("dialog");
    dialog.id = "acpos-core-draft-dialog";
    dialog.style.padding = "20px";
    dialog.style.border = "1px solid #3a4458";
    dialog.style.borderRadius = "12px";
    dialog.style.background = "#10151f";
    dialog.style.color = "#e8edf7";
    dialog.style.minWidth = "360px";
    const titleLabel = kind === "PROJECT" ? "Project title" : "Topic title";
    const codeLabel = kind === "PROJECT" ? "Project code" : "Topic code";
    const codeName = kind === "PROJECT" ? "project_code" : "topic_code";
    dialog.innerHTML = `<form method="dialog" id="acpos-core-draft-form" style="display:grid;gap:12px">
      <strong>${kind === "PROJECT" ? "Create project draft" : "Create topic draft"}</strong>
      <label style="display:grid;gap:4px">${titleLabel}<input name="title" required autocomplete="off" style="padding:8px"></label>
      <label style="display:grid;gap:4px">${codeLabel}<input name="${codeName}" required autocomplete="off" style="padding:8px"></label>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button value="cancel" type="button" id="acpos-core-draft-cancel">Cancel</button>
        <button value="ok">Save</button>
      </div>
    </form>`;
    document.body.appendChild(dialog);
    const form = dialog.querySelector("form") as HTMLFormElement;
    const finish = (result: { ok: true; payload: Record<string, unknown> } | { ok: false; reason_code: string }) => {
      dialog.close();
      dialog.remove();
      resolve(result);
    };
    dialog.querySelector("#acpos-core-draft-cancel")?.addEventListener("click", () => {
      finish({ ok: false, reason_code: "DRAFT_FORM_CANCELLED" });
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const title = String(data.get("title") ?? "").trim();
      const code = String(data.get(codeName) ?? "").trim();
      if (!title || !code) {
        finish({ ok: false, reason_code: "DRAFT_FORM_FIELDS_REQUIRED" });
        return;
      }
      finish({ ok: true, payload: { title, [codeName]: code } });
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish({ ok: false, reason_code: "DRAFT_FORM_CANCELLED" });
    });
    if (typeof dialog.showModal === "function") dialog.showModal();
    else finish({ ok: false, reason_code: "DRAFT_FORM_DIALOG_UNSUPPORTED" });
  });
}

function bindStrategyAdminHttpCommandAdapter(): void {
  configureStrategyAdminCommandAdapter({
    invoke: async (input) => {
      if (input.operation === "searchProjection" || input.operation === "refreshProjection") {
        const path = input.operation === "searchProjection" ? "/v1/search" : "/v1/projections/refresh";
        const response = await fetch(path, {
          method: "POST",
          cache: "no-store",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            ...input.payload,
            current_page_uid: "admin:STR-01",
            page_uid: "admin:STR-01",
            source_page_uid: input.source_page_uid,
          }),
        });
        const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
        const raw: unknown = await response.json().catch(() => null);
        const body = rec(raw);
        if (!response.ok) {
          return {
            ok: false,
            reason_code: typeof body?.reason_code === "string" ? body.reason_code : "STR_ADMIN_COMMAND_FAILED",
            correlation_id,
          };
        }
        return { ok: true, value: raw, correlation_id };
      }
      if (input.operation === "configureGovernedResource" || input.operation === "approveGovernedResource") {
        const resourceId = typeof input.payload.resource_id === "string" ? input.payload.resource_id.trim() : "";
        if (!resourceId) {
          return { ok: false, reason_code: "STR_ADMIN_GOVERNED_RESOURCE_ID_REQUIRED", correlation_id: "unresolved" };
        }
        const suffix = input.operation === "approveGovernedResource" ? "/approve" : "";
        const response = await fetch(`/v1/governance/resources/${encodeURIComponent(resourceId)}${suffix}`, {
          method: input.operation === "approveGovernedResource" ? "POST" : "PATCH",
          cache: "no-store",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            ...input.payload,
            current_page_uid: "admin:STR-01",
            page_uid: "admin:STR-01",
            source_page_uid: input.source_page_uid,
          }),
        });
        const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
        const raw: unknown = await response.json().catch(() => null);
        const body = rec(raw);
        if (!response.ok) {
          return {
            ok: false,
            reason_code: typeof body?.reason_code === "string" ? body.reason_code : "STR_ADMIN_GOVERNANCE_COMMAND_FAILED",
            correlation_id,
          };
        }
        return { ok: true, value: raw, correlation_id };
      }
      return { ok: false, reason_code: "STR_ADMIN_OPERATION_RUNTIME_NOT_MATERIALIZED", correlation_id: "unresolved" };
    },
  });
}

export function bindIdentityClientCommandAdapters(): void {
  if (bound) return;
  bound = true;
  bindStrategyAdminHttpCommandAdapter();
  if (isControlledTestMode()) return;

  configureCoreCreationPermissionAdapter({
    authorizeCreation: async ({ required_permission_uid }) => {
      try {
        const response = await fetch("/v1/identity/session", { method: "GET", cache: "no-store", credentials: "include" });
        const raw: unknown = await response.json().catch(() => null);
        const body = rec(raw);
        if (!response.ok || body?.logged_in !== true) {
          return { allowed: false, reason_code: "IDENTITY_RUNTIME_NOT_BOUND", required_permission_uid };
        }
        return { allowed: true, required_permission_uid };
      } catch {
        return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED", required_permission_uid };
      }
    },
  });

  configureCoreDraftFormAdapter({
    openRegisteredForm: (context) => openDraftDialog(context.kind),
  });

  configureCoreConversationPayloadAdapter({
    buildThreadCreatePayload: (context) => ({ ok: true, payload: { ...context } }),
    buildMessageSendPayload: (context) => ({ ok: true, payload: { ...context } }),
  });

  configureCoreCandidatePayloadAdapter({
    buildCreatePayload: (context) => ({ ok: true, payload: { ...context } }),
    buildDecisionPayload: (context) => ({ ok: true, payload: { ...context } }),
  });

  configureCoreLockCommandPayloadAdapter({
    buildPayload: (context) => ({ ok: true, payload: { ...context } }),
  });

  configureCoreComposerResourceAdapter({
    selectResource: (context) => {
      const ref = typeof window !== "undefined" ? window.prompt(`${context.kind} ref`) : null;
      if (!ref || !ref.trim()) return { ok: false, reason_code: `${context.kind}_REF_REQUIRED` };
      return { ok: true, ref: ref.trim() };
    },
  });

  configureDevCommandAdapter({
    invoke: async (input) => {
      const binding = DEV_CONTROL_BINDINGS[input.control_uid as DevControlUid];
      if (!binding || binding.action_uid !== input.action_uid || !binding.operation) {
        return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_COMMAND_BINDING_UNREGISTERED", correlation_id: "unresolved" };
      }

      const jobRef = input.projection?.values["DEV-01-FLD-JOB-REF"] ?? "";
      let path: string;
      let payload: Record<string, unknown> = {};
      if (binding.operation === "startCompanyDiscovery") {
        path = "/v1/outreach/discovery-jobs";
        payload = {
          job_name: "ACPOS Company Discovery",
          mode: "SINGLE_RUN",
          search_scope: {},
          allowed_sources: [],
          interval_seconds: 3600,
          result_limit: 50,
        };
      } else if (
        binding.operation === "pauseCompanyDiscovery"
        || binding.operation === "resumeCompanyDiscovery"
        || binding.operation === "stopCompanyDiscovery"
      ) {
        if (!jobRef || jobRef === "—") {
          return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_DISCOVERY_JOB_ID_REQUIRED", correlation_id: "unresolved" };
        }
        const suffix = binding.operation === "pauseCompanyDiscovery"
          ? "pause"
          : binding.operation === "resumeCompanyDiscovery"
            ? "resume"
            : "stop";
        path = `/v1/outreach/discovery-jobs/${encodeURIComponent(jobRef)}/${suffix}`;
      } else {
        return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_COMMAND_RUNTIME_NOT_MATERIALIZED", correlation_id: "unresolved" };
      }

      const response = await fetch(path, {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: { "content-type": "application/json", "x-correlation-id": crypto.randomUUID() },
        body: JSON.stringify(payload),
      });
      const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
      const raw: unknown = await response.json().catch(() => null);
      const body = rec(raw);
      if (!response.ok) {
        return {
          ok: false,
          error_uid: "DEV-01-ERR-UNDEFINED",
          reason_code: typeof body?.reason_code === "string" ? body.reason_code : "DEV_COMMAND_REQUEST_FAILED",
          correlation_id,
        };
      }

      const refreshed = await readDevProjection();
      if (!refreshed.ok) return refreshed;
      return { ok: true, projection: refreshed.projection, correlation_id };
    },
  });

  configureIamClientCommandAdapter({
    invoke: async (input) => {
      if (input.action_uid === "IAM-01-ACT-SEARCH") {
        const projectionResult = await readIamProjection();
        if (!projectionResult.ok) return projectionResult;
        const query = String(rec(input.client_state)?.search_query ?? "").trim().toLowerCase();
        const accounts = query
          ? projectionResult.projection.accounts.filter((item) => {
            const email = item.basic_data.email ?? "";
            return item.label.toLowerCase().includes(query) || item.account_id.toLowerCase().includes(query) || email.toLowerCase().includes(query);
          })
          : projectionResult.projection.accounts;
        return {
          ok: true,
          projection: { ...projectionResult.projection, accounts, authorized_account_count: accounts.length },
          correlation_id: projectionResult.correlation_id,
        };
      }
      return {
        ok: false,
        error_uid: "IAM-01-ERR-UNDEFINED",
        reason_code: "IAM01_WRITE_RUNTIME_NOT_MATERIALIZED",
        correlation_id: "unresolved",
      };
    },
  });

  configureDbClientRuntime({
    readProjection: async () => {
      const response = await fetch("/v1/ui-projections/admin%3ADB-01", { method: "GET", cache: "no-store", credentials: "include" });
      const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
      const raw: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const body = rec(raw);
        return { ok: false, error_uid: "DB-01-ERR-CONTEXT-001", reason_code: typeof body?.reason_code === "string" ? body.reason_code : "DB_PROJECTION_READ_FAILED", correlation_id };
      }
      return { ok: true, projection: normalizeDbProjection(raw), correlation_id };
    },
    read: async (port_uid, input) => {
      const response = await fetch("/v1/database/read", {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ port_uid, scope: input.scope, query: input.query }),
      });
      const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
      const raw: unknown = await response.json().catch(() => null);
      const body = rec(raw);
      if (!response.ok) {
        return { ok: false, error_uid: "DB-01-ERR-CONTEXT-001", reason_code: typeof body?.reason_code === "string" ? body.reason_code : "DB_READ_MODEL_QUERY_FAILED", correlation_id };
      }
      return { ok: true, projection: normalizeDbProjection(body?.projection ?? raw), correlation_id };
    },
    resolveSystemLifecycle: async () => ({ ok: true, href: "/admin/system" }),
  });

  configureInfoCommandPayloadBuilder({
    build: (input) => {
      const payload = {
        page_uid: "workspace:INFO-01",
        query: input.scope_filter ?? "",
        projection_version: input.projection_version,
        authorized_scope: input.authorized_scope,
        scope_filter: input.scope_filter,
        candidate_ref: input.candidate_ref,
      };
      if (input.action_uid === "INFO-01-ACT-ADOPT-CONTEXT") {
        if (!input.candidate_ref) throw new Error("INFO_CONTEXT_CANDIDATE_REQUIRED");
        return { path_params: { id: input.candidate_ref }, payload };
      }
      if (input.action_uid === "INFO-01-ACT-CANDIDATE-DECIDE") {
        if (!input.candidate_ref) throw new Error("INFO_CANDIDATE_REQUIRED");
        return { path_params: { id: input.candidate_ref }, payload: { ...payload, decision: "ACCEPTED" } };
      }
      return { payload };
    },
  });

  configureStrategyRequestBuilder({
    build: (input) => {
      if (input.action_uid === "STR-01-ACT-SEND") {
        return {
          path_params: { conversationId: input.conversation_id ?? "" },
          payload: {
            page_uid: "workspace:STR-01",
            topic_ref: input.topic_ref,
            message: input.message,
            attachment_refs: [...input.attachment_refs],
            mode: input.mode,
          },
        };
      }
      if (input.action_uid === "STR-01-ACT-STOP") {
        return {
          path_params: { conversationId: input.conversation_id ?? "" },
          payload: { page_uid: "workspace:STR-01", topic_ref: input.topic_ref, mode: input.mode },
        };
      }
      if (input.action_uid === "STR-01-ACT-COMPARE") {
        return { query: { candidate_refs: input.compare_candidate_refs.join(",") } };
      }
      if (input.action_uid === "STR-01-ACT-REVIEW") {
        return {
          payload: {
            page_uid: "workspace:STR-01",
            candidate_ref: input.candidate_ref,
            candidate_version_ref: input.candidate_version_ref,
          },
        };
      }
      return {
        payload: {
          page_uid: "workspace:STR-01",
          candidate_ref: input.candidate_ref,
          candidate_version_ref: input.candidate_version_ref,
        },
      };
    },
  });

}
