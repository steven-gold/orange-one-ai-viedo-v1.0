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
import { DEV_CONTROL_BINDINGS, type DevControlBinding, type DevControlUid } from "@/domain/dev/devControlBindings";
import { configureSocCommandAdapter } from "@/domain/social/socCommandPort";
import { readSocProjection } from "@/domain/social/socProjectionPort";

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


type InfoHumanDecisionResult =
  | { ok: true; decision_reason: string; decision?: "ACCEPTED" | "REJECTED" }
  | { ok: false; reason_code: string };

function openInfoHumanDecisionDialog(kind: "ADOPT" | "DECIDE"): Promise<InfoHumanDecisionResult> {
  if (typeof document === "undefined") {
    return Promise.resolve({ ok: false, reason_code: "INFO_HUMAN_DECISION_WINDOW_UNAVAILABLE" });
  }
  return new Promise((resolve) => {
    document.getElementById("acpos-info-human-decision-dialog")?.remove();
    const dialog = document.createElement("dialog");
    dialog.id = "acpos-info-human-decision-dialog";
    dialog.style.padding = "20px";
    dialog.style.border = "1px solid #3a4458";
    dialog.style.borderRadius = "12px";
    dialog.style.background = "#10151f";
    dialog.style.color = "#e8edf7";
    dialog.style.minWidth = "420px";
    const isAdopt = kind === "ADOPT";
    dialog.innerHTML = `<form method="dialog" id="acpos-info-human-decision-form" style="display:grid;gap:12px">
      <strong>${isAdopt ? "Adopt context candidate" : "Decide context candidate"}</strong>
      ${isAdopt ? "" : `<label style="display:grid;gap:4px">Decision
        <select name="decision" required style="padding:8px">
          <option value="ACCEPTED">Accept</option>
          <option value="REJECTED">Reject</option>
        </select>
      </label>`}
      <label style="display:grid;gap:4px">Decision reason
        <textarea name="decision_reason"${isAdopt ? " required" : ""} rows="4" autocomplete="off" style="padding:8px"></textarea>
      </label>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button value="cancel" type="button" id="acpos-info-human-decision-cancel">Cancel</button>
        <button value="ok">${isAdopt ? "Adopt" : "Submit decision"}</button>
      </div>
    </form>`;
    document.body.appendChild(dialog);
    const form = dialog.querySelector("form") as HTMLFormElement;
    let settled = false;
    const finish = (result: InfoHumanDecisionResult) => {
      if (settled) return;
      settled = true;
      if (dialog.open) dialog.close();
      dialog.remove();
      resolve(result);
    };
    dialog.querySelector("#acpos-info-human-decision-cancel")?.addEventListener("click", () => {
      finish({ ok: false, reason_code: "INFO_HUMAN_DECISION_CANCELLED" });
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const decision_reason = String(data.get("decision_reason") ?? "").trim();
      if (isAdopt) {
        if (!decision_reason) {
          finish({ ok: false, reason_code: "INFO01_DECISION_REASON_REQUIRED" });
          return;
        }
        finish({ ok: true, decision_reason });
        return;
      }
      const decision = String(data.get("decision") ?? "").trim();
      if (decision !== "ACCEPTED" && decision !== "REJECTED") {
        finish({ ok: false, reason_code: "INFO01_REGISTERED_DECISION_REQUIRED" });
        return;
      }
      finish({ ok: true, decision, decision_reason });
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish({ ok: false, reason_code: "INFO_HUMAN_DECISION_CANCELLED" });
    });
    if (typeof dialog.showModal === "function") dialog.showModal();
    else finish({ ok: false, reason_code: "INFO_HUMAN_DECISION_DIALOG_UNSUPPORTED" });
  });
}


type SocPolicyDialogResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

function openSocTargetPolicyDialog(projection: import("@/domain/social/socProjectionPort").SocNormalizedProjection): Promise<SocPolicyDialogResult> {
  if (typeof document === "undefined") return Promise.resolve({ ok: false, reason_code: "SOC_POLICY_WINDOW_UNAVAILABLE" });
  return new Promise((resolve) => {
    document.getElementById("acpos-soc-target-policy-dialog")?.remove();
    const dialog=document.createElement("dialog");
    dialog.id="acpos-soc-target-policy-dialog";
    dialog.style.padding="20px";
    dialog.style.border="1px solid #3a4458";
    dialog.style.borderRadius="12px";
    dialog.style.background="#10151f";
    dialog.style.color="#e8edf7";
    dialog.style.minWidth="480px";
    dialog.innerHTML=`<form method="dialog" style="display:grid;gap:10px">
      <strong>Configure target posting policy</strong>
      <label>minimum_interval_hours<input name="minimum_interval_hours" type="number" min="0" step="1" required></label>
      <label>daily_limit<input name="daily_limit" type="number" min="0" step="1" required></label>
      <label>weekly_limit<input name="weekly_limit" type="number" min="0" step="1" required></label>
      <label>same_content_cooldown_hours<input name="same_content_cooldown_hours" type="number" min="0" step="1"></label>
      <label>similar_content_cooldown_hours<input name="similar_content_cooldown_hours" type="number" min="0" step="1"></label>
      <label>allowed_time_window<textarea name="allowed_time_window" rows="3"></textarea></label>
      <label>target_rule_notes<textarea name="target_rule_notes" rows="3"></textarea></label>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button type="button" id="acpos-soc-policy-cancel">Cancel</button>
        <button value="ok">Save policy</button>
      </div>
    </form>`;
    document.body.appendChild(dialog);
    const form=dialog.querySelector("form") as HTMLFormElement;
    const setValue=(name:string,key:string)=>{
      const field=form.elements.namedItem(name) as HTMLInputElement|HTMLTextAreaElement|null;
      const current=projection.values[key];
      if(field&&current&&current!=="—")field.value=current;
    };
    setValue("minimum_interval_hours","SOC-01-FLD-MIN-INTERVAL");
    setValue("daily_limit","SOC-01-FLD-DAILY-LIMIT");
    setValue("weekly_limit","SOC-01-FLD-WEEKLY-LIMIT");
    setValue("same_content_cooldown_hours","SOC-01-FLD-SAME-COOLDOWN");
    setValue("similar_content_cooldown_hours","SOC-01-FLD-SIMILAR-COOLDOWN");
    setValue("allowed_time_window","SOC-01-FLD-ALLOWED-WINDOW");
    setValue("target_rule_notes","SOC-01-FLD-TARGET-RULE-NOTES");
    let settled=false;
    const finish=(result:SocPolicyDialogResult)=>{if(settled)return;settled=true;if(dialog.open)dialog.close();dialog.remove();resolve(result)};
    dialog.querySelector("#acpos-soc-policy-cancel")?.addEventListener("click",()=>finish({ok:false,reason_code:"SOC_POLICY_CANCELLED"}));
    form.addEventListener("submit",(event)=>{
      event.preventDefault();
      const data=new FormData(form);
      const requiredNumber=(name:string)=>Number(String(data.get(name)??""));
      const minimum_interval_hours=requiredNumber("minimum_interval_hours");
      const daily_limit=requiredNumber("daily_limit");
      const weekly_limit=requiredNumber("weekly_limit");
      if(![minimum_interval_hours,daily_limit,weekly_limit].every((n)=>Number.isSafeInteger(n)&&n>=0)){
        finish({ok:false,reason_code:"SOC01_REQUIRED_POLICY_FIELD_MISSING"});return;
      }
      const payload:Record<string,unknown>={minimum_interval_hours,daily_limit,weekly_limit};
      for(const key of ["same_content_cooldown_hours","similar_content_cooldown_hours"]){
        const raw=String(data.get(key)??"").trim();
        if(raw){
          const parsed=Number(raw);
          if(!Number.isSafeInteger(parsed)||parsed<0){finish({ok:false,reason_code:"SOC01_POLICY_INTEGER_INVALID"});return;}
          payload[key]=parsed;
        }
      }
      const windowRaw=String(data.get("allowed_time_window")??"").trim();
      if(windowRaw){
        try{
          const parsed:unknown=JSON.parse(windowRaw);
          if(!parsed||typeof parsed!=="object"||Array.isArray(parsed))throw new Error("invalid");
          payload.allowed_time_window=parsed;
        }catch{finish({ok:false,reason_code:"SOC01_ALLOWED_TIME_WINDOW_INVALID"});return;}
      }
      const notes=String(data.get("target_rule_notes")??"").trim();
      if(notes)payload.target_rule_notes=notes;
      finish({ok:true,payload});
    });
    dialog.addEventListener("cancel",(event)=>{event.preventDefault();finish({ok:false,reason_code:"SOC_POLICY_CANCELLED"})});
    if(typeof dialog.showModal==="function")dialog.showModal();else finish({ok:false,reason_code:"SOC_POLICY_DIALOG_UNSUPPORTED"});
  });
}



type SocCandidateDecisionDialogResult =
  | { ok: true; decision: "APPROVE" | "REJECT" | "RETURN"; rationale: string }
  | { ok: false; reason_code: string };

function openSocCandidateDecisionDialog(): Promise<SocCandidateDecisionDialogResult> {
  if (typeof document === "undefined") {
    return Promise.resolve({ ok: false, reason_code: "SOC_CANDIDATE_WINDOW_UNAVAILABLE" });
  }
  return new Promise((resolve) => {
    document.getElementById("acpos-soc-candidate-decision-dialog")?.remove();
    const dialog = document.createElement("dialog");
    dialog.id = "acpos-soc-candidate-decision-dialog";
    dialog.style.padding = "20px";
    dialog.style.border = "1px solid #3a4458";
    dialog.style.borderRadius = "12px";
    dialog.style.background = "#10151f";
    dialog.style.color = "#e8edf7";
    dialog.style.minWidth = "440px";
    dialog.innerHTML = `<form method="dialog" style="display:grid;gap:12px">
      <strong>審查內容 Candidate</strong>
      <label style="display:grid;gap:4px">Decision
        <select name="decision" required>
          <option value="">—</option>
          <option value="APPROVE">APPROVE</option>
          <option value="REJECT">REJECT</option>
          <option value="RETURN">RETURN</option>
        </select>
      </label>
      <label style="display:grid;gap:4px">Rationale
        <textarea name="rationale" rows="4" required autocomplete="off"></textarea>
      </label>
      <small>APPROVE 只封板 exact content package；此動作不建立發佈要求，也不代表外部平台已發佈。</small>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button type="button" id="acpos-soc-candidate-cancel">取消</button>
        <button value="ok">送出審查</button>
      </div>
    </form>`;
    document.body.appendChild(dialog);
    const form = dialog.querySelector("form") as HTMLFormElement;
    let settled = false;
    const finish = (result: SocCandidateDecisionDialogResult) => {
      if (settled) return;
      settled = true;
      if (dialog.open) dialog.close();
      dialog.remove();
      resolve(result);
    };
    dialog.querySelector("#acpos-soc-candidate-cancel")?.addEventListener("click", () => {
      finish({ ok: false, reason_code: "SOC_CANDIDATE_DECISION_CANCELLED" });
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const decision = String(data.get("decision") ?? "").trim();
      const rationale = String(data.get("rationale") ?? "").trim();
      if (decision !== "APPROVE" && decision !== "REJECT" && decision !== "RETURN") {
        finish({ ok: false, reason_code: "SOC01_CANDIDATE_DECISION_INVALID" });
        return;
      }
      if (!rationale) {
        finish({ ok: false, reason_code: "SOC01_CANDIDATE_RATIONALE_REQUIRED" });
        return;
      }
      finish({ ok: true, decision, rationale });
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish({ ok: false, reason_code: "SOC_CANDIDATE_DECISION_CANCELLED" });
    });
    if (typeof dialog.showModal === "function") dialog.showModal();
    else finish({ ok: false, reason_code: "SOC_CANDIDATE_DIALOG_UNSUPPORTED" });
  });
}

function openSocPublishRequestConfirm(input: {
  target_id: string;
  content_package_id: string;
  channel_account_id: string;
}): Promise<{ok:true}|{ok:false;reason_code:string}> {
  if (typeof document === "undefined") return Promise.resolve({ok:false,reason_code:"SOC_PUBLISH_WINDOW_UNAVAILABLE"});
  return new Promise((resolve) => {
    document.getElementById("acpos-soc-publish-confirm-dialog")?.remove();
    const dialog=document.createElement("dialog");
    dialog.id="acpos-soc-publish-confirm-dialog";
    dialog.style.padding="20px";
    dialog.style.border="1px solid #3a4458";
    dialog.style.borderRadius="12px";
    dialog.style.background="#10151f";
    dialog.style.color="#e8edf7";
    dialog.style.minWidth="440px";
    dialog.innerHTML=`<form method="dialog" style="display:grid;gap:12px">
      <strong>建立發佈要求</strong>
      <div data-field="target"></div>
      <div data-field="content"></div>
      <div data-field="channel"></div>
      <small>此步驟只建立 PENDING_EXTERNAL 要求，不代表外部平台已發佈成功。</small>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button type="button" id="acpos-soc-publish-cancel">取消</button>
        <button value="ok">確認建立</button>
      </div>
    </form>`;
    document.body.appendChild(dialog);
    const form=dialog.querySelector("form") as HTMLFormElement;
    const setText=(field:string,value:string)=>{
      const node=dialog.querySelector(`[data-field="${field}"]`);
      if(node)node.textContent=value;
    };
    setText("target",`Target: ${input.target_id}`);
    setText("content",`Content package: ${input.content_package_id}`);
    setText("channel",`Channel account: ${input.channel_account_id}`);
    let settled=false;
    const finish=(result:{ok:true}|{ok:false;reason_code:string})=>{
      if(settled)return;settled=true;if(dialog.open)dialog.close();dialog.remove();resolve(result);
    };
    dialog.querySelector("#acpos-soc-publish-cancel")?.addEventListener("click",()=>finish({ok:false,reason_code:"SOC_PUBLISH_CANCELLED"}));
    form.addEventListener("submit",(event)=>{event.preventDefault();finish({ok:true})});
    dialog.addEventListener("cancel",(event)=>{event.preventDefault();finish({ok:false,reason_code:"SOC_PUBLISH_CANCELLED"})});
    if(typeof dialog.showModal==="function")dialog.showModal();else finish({ok:false,reason_code:"SOC_PUBLISH_DIALOG_UNSUPPORTED"});
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
      const binding = DEV_CONTROL_BINDINGS[input.control_uid as DevControlUid] as DevControlBinding | undefined;
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

  configureSocCommandAdapter({
    supports: (action_uid) => [
      "SOC-01-ACT-CONTENT-SAVE",
      "SOC-01-ACT-CANDIDATE-DECIDE",
      "SOC-01-ACT-POLICY-CONFIG",
      "SOC-01-ACT-PUBLISH-REQUEST",
      "SOC-01-ACT-REFRESH",
    ].includes(action_uid),
    invoke: async (input) => {
      if (input.action_uid === "SOC-01-ACT-REFRESH") {
        const refreshed = await readSocProjection();
        return refreshed.ok
          ? { ok: true as const, projection: refreshed.projection, correlation_id: refreshed.correlation_id }
          : refreshed;
      }

      const projection = input.projection;
      if (!projection) {
        return { ok: false as const, error_uid: "SOC-01-ERR-CONTENT", reason_code: "SOC_PROJECTION_REQUIRED", correlation_id: "unresolved" };
      }

      const contentPackageId = projection.values["SOC-01-FLD-CONTENT-PACKAGE"] ?? "";
      const candidateRef = projection.values["SOC-01-FLD-CANDIDATE-REF"] ?? "";
      const versionText = projection.values["SOC-01-FLD-CANDIDATE-VERSION"] ?? "";
      const candidateVersion = Number(versionText);
      let path: string;
      let payload: Record<string, unknown>;
      let method = "POST";

      if (input.action_uid === "SOC-01-ACT-POLICY-CONFIG") {
        const targetId=projection.selected.target_id??"";
        const targetVersion=Number(projection.selected.target_version??"");
        if(!targetId||!Number.isSafeInteger(targetVersion)||targetVersion<1){
          return {ok:false as const,error_uid:"SOC-01-ERR-UNDEFINED",reason_code:"SOC01_TARGET_POLICY_CONTEXT_REQUIRED",correlation_id:"unresolved"};
        }
        const dialog=await openSocTargetPolicyDialog(projection);
        if(!dialog.ok)return {ok:false as const,error_uid:"SOC-01-ERR-UNDEFINED",reason_code:dialog.reason_code,correlation_id:"unresolved"};
        path=`/v1/social/targets/${encodeURIComponent(targetId)}/posting-policy`;
        method="PUT";
        payload={
          target_id:targetId,
          scope:{},
          expected_version:targetVersion,
          idempotency_key:`soc-policy:${targetId}:${crypto.randomUUID()}`,
          ...dialog.payload,
        };
      } else if (input.action_uid === "SOC-01-ACT-PUBLISH-REQUEST") {
        const targetId=projection.selected.target_id??"";
        const targetVersion=Number(projection.selected.target_version??"");
        const publishContentPackageId=projection.selected.content_package_id??contentPackageId;
        const channelAccountId=projection.selected.channel_account_id??"";
        const contentHash=projection.selected.content_hash??"";
        if(!targetId||!Number.isSafeInteger(targetVersion)||targetVersion<1||!publishContentPackageId||publishContentPackageId==="—"||!channelAccountId){
          return {ok:false as const,error_uid:"SOC-01-ERR-PUBLISH",reason_code:"SOC01_PUBLISH_CONTEXT_REQUIRED",correlation_id:"unresolved"};
        }
        const confirm=await openSocPublishRequestConfirm({
          target_id:targetId,
          content_package_id:publishContentPackageId,
          channel_account_id:channelAccountId,
        });
        if(!confirm.ok)return {ok:false as const,error_uid:"SOC-01-ERR-PUBLISH",reason_code:confirm.reason_code,correlation_id:"unresolved"};
        path=`/v1/social/targets/${encodeURIComponent(targetId)}/publish`;
        payload={
          target_id:targetId,
          content_package_id:publishContentPackageId,
          channel_account_id:channelAccountId,
          scope:{},
          expected_version:targetVersion,
          idempotency_key:`soc-publish:${targetId}:${crypto.randomUUID()}`,
          ...(contentHash?{content_hash:contentHash}:{}),
        };
      } else if (input.action_uid === "SOC-01-ACT-CONTENT-SAVE") {
        if (!contentPackageId || contentPackageId === "—") {
          return { ok: false as const, error_uid: "SOC-01-ERR-CONTENT", reason_code: "SOC01_CONTENT_PACKAGE_REQUIRED", correlation_id: "unresolved" };
        }
        path = "/v1/drafts";
        payload = {
          page_uid: "admin:SOC-01",
          content_package_id: contentPackageId,
          idempotency_key: `soc-draft:${contentPackageId}:${crypto.randomUUID()}`,
          ...(candidateRef && candidateRef !== "—" ? { draft_id: candidateRef } : {}),
          ...(Number.isSafeInteger(candidateVersion) && candidateVersion > 0 ? { expected_version: candidateVersion } : {}),
        };
      } else if (input.action_uid === "SOC-01-ACT-CANDIDATE-DECIDE") {
        if (!candidateRef || candidateRef === "—" || !Number.isSafeInteger(candidateVersion) || candidateVersion < 1) {
          return { ok: false as const, error_uid: "SOC-01-ERR-CONTENT", reason_code: "SOC01_CANDIDATE_REQUIRED", correlation_id: "unresolved" };
        }
        const decisionDialog = await openSocCandidateDecisionDialog();
        if (!decisionDialog.ok) {
          return { ok: false as const, error_uid: "SOC-01-ERR-CONTENT", reason_code: decisionDialog.reason_code, correlation_id: "unresolved" };
        }
        path = `/v1/candidates/${encodeURIComponent(candidateRef)}/decision`;
        payload = {
          page_uid: "admin:SOC-01",
          candidate_id: candidateRef,
          expected_version: candidateVersion,
          decision: decisionDialog.decision,
          rationale: decisionDialog.rationale,
        };
      } else {
        return { ok: false as const, error_uid: "SOC-01-ERR-UNDEFINED", reason_code: "SOC_COMMAND_RUNTIME_NOT_MATERIALIZED", correlation_id: "unresolved" };
      }

      const response = await fetch(path, {
        method,
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
          ok: false as const,
          error_uid: "SOC-01-ERR-CONTENT",
          reason_code: typeof body?.reason_code === "string" ? body.reason_code : "SOC_COMMAND_REQUEST_FAILED",
          correlation_id,
        };
      }

      const refreshed = await readSocProjection();
      if (!refreshed.ok) return refreshed;
      return { ok: true as const, projection: refreshed.projection, correlation_id };
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
    build: async (input) => {
      const scope_ref = input.scope_filter ?? input.authorized_scope ?? "workspace:INFO-01";
      const payload = {
        page_uid: "workspace:INFO-01",
        query: input.scope_filter ?? "",
        projection_type: "INFO_WORKSPACE",
        scope_ref,
        projection_version: input.projection_version,
        authorized_scope: input.authorized_scope,
        scope_filter: input.scope_filter,
        candidate_ref: input.candidate_ref,
      };
      if (input.action_uid === "INFO-01-ACT-EXPORT") {
        throw new Error("INFO_EXPORT_OWNER_NOT_MATERIALIZED");
      }
      if (input.action_uid === "INFO-01-ACT-ADOPT-CONTEXT") {
        if (!input.candidate_ref) throw new Error("INFO_CONTEXT_CANDIDATE_REQUIRED");
        const human = await openInfoHumanDecisionDialog("ADOPT");
        if (!human.ok) throw new Error(human.reason_code);
        return {
          path_params: { id: input.candidate_ref },
          payload: {
            ...payload,
            context_candidate_id: input.candidate_ref,
            decision_reason: human.decision_reason,
          },
        };
      }
      if (input.action_uid === "INFO-01-ACT-CANDIDATE-DECIDE") {
        if (!input.candidate_ref) throw new Error("INFO_CANDIDATE_REQUIRED");
        const human = await openInfoHumanDecisionDialog("DECIDE");
        if (!human.ok) throw new Error(human.reason_code);
        return {
          path_params: { id: input.candidate_ref },
          payload: {
            ...payload,
            candidate_id: input.candidate_ref,
            decision: human.decision,
            decision_reason: human.decision_reason || undefined,
          },
        };
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
