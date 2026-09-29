"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { readErpProjection, type ErpNormalizedProjection } from "@/domain/erp/erpProjectionPort";
import { configureErpCommandAdapter, invokeErpCommand, isErpCommandAdapterBound, type ErpCommandResult } from "@/domain/erp/erpCommandPort";
import { ERP_CONTROL_BINDINGS, type ErpControlBinding, type ErpControlUid } from "@/domain/erp/erpControlBindings";

type AdapterResult = { ok: true; correlation_id: string } | { ok: false; status: number; reason_code: string; correlation_id: string };

function newId() {
  try { return crypto.randomUUID(); } catch { return `id-${Date.now()}-${Math.random().toString(36).slice(2)}`; }
}
function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  if (typeof value === "string" && value.trim()) return value.split(",").map(item => item.trim()).filter(Boolean);
  return [];
}
function optionalNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}
function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
function errorUid(status: number, reason: string) {
  if (status === 403) return "ERP-01-ERR-AUTH";
  if (reason.includes("SECRET")) return "ERP-01-ERR-SECRET";
  if (reason.includes("UNREGISTERED_WRITE") || reason.includes("FORBIDDEN_WRITE")) return "ERP-01-ERR-UNREGISTERED-WRITE";
  if (status === 409 || reason.includes("VERSION")) return "ERP-01-ERR-VERSION";
  if (reason.includes("CONNECTOR") || reason.includes("MAPPING")) return "ERP-01-ERR-CONNECTOR";
  if (reason.includes("SYNC") || reason.includes("SNAPSHOT")) return "ERP-01-ERR-SYNC";
  if (reason.includes("FINANCE")) return "ERP-01-ERR-FINANCE";
  return "ERP-01-ERR-UNDEFINED";
}

async function callJson(url: string, method: string, body: unknown, correlation_id: string): Promise<AdapterResult> {
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: { "content-type": "application/json", "x-correlation-id": correlation_id },
      body: method === "GET" ? undefined : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 503, reason_code: "ERP_COMMAND_REQUEST_FAILED", correlation_id };
  }
  const raw: unknown = await response.json().catch(() => null);
  const record = raw && typeof raw === "object" ? raw as Record<string,unknown> : null;
  const serverCorrelation = typeof record?.correlation_id === "string" ? record.correlation_id : response.headers.get("x-correlation-id") ?? correlation_id;
  if (!response.ok) {
    return { ok: false, status: response.status, reason_code: typeof record?.reason_code === "string" ? record.reason_code : "ERP_COMMAND_REJECTED", correlation_id: serverCorrelation };
  }
  return { ok: true, correlation_id: serverCorrelation };
}

configureErpCommandAdapter({
  invoke: async ({ action_uid, projection, form }) => {
    if (!projection) return { ok: false, error_uid: "ERP-01-ERR-UNDEFINED", reason_code: "ERP_COMMAND_PROJECTION_NOT_READY", correlation_id: "unresolved" };
    const correlation_id = newId();
    const selected = projection.selected ?? {};
    const connectorId = selected.connector_id ?? "";
    const jobId = selected.sync_job_id ?? "";
    const failureId = selected.failure_id ?? "";
    const input = form ?? {};
    const idempotencyKey = newId();
    const execute = async (url: string, method: string, body: unknown): Promise<ErpCommandResult> => {
      const result = await callJson(url, method, body, correlation_id);
      if (!result.ok) return { ok: false, error_uid: errorUid(result.status, result.reason_code), reason_code: result.reason_code, correlation_id: result.correlation_id };
      const refreshed = await readErpProjection();
      if (!refreshed.ok) return { ok: false, error_uid: refreshed.error_uid, reason_code: `ERP_PROJECTION_REFRESH_AFTER_COMMAND_FAILED:${refreshed.reason_code}`, correlation_id: result.correlation_id };
      return { ok: true, projection: refreshed.projection, correlation_id: result.correlation_id };
    };

    switch (action_uid) {
      case "ERP-01-ACT-CONNECTOR-CREATE":
        return execute("/v1/erp/connectors", "POST", {
          provider_key: optionalString(input.provider_key), adapter_key: optionalString(input.adapter_key), secret_reference_id: optionalString(input.secret_reference_id),
          entity_scope: optionalString(input.entity_scope), mapping_version: optionalNumber(input.mapping_version), mapping_entity_name: optionalString(input.mapping_entity_name),
          mapping_source_schema: optionalString(input.mapping_source_schema), mapping_target_schema: optionalString(input.mapping_target_schema), mapping_transform_spec: optionalString(input.mapping_transform_spec),
          data_classification: optionalString(input.data_classification), scope: optionalString(input.entity_scope), expected_version: optionalNumber(selected.connector_version), idempotency_key: idempotencyKey,
        });
      case "ERP-01-ACT-CONNECTOR-UPDATE":
        return execute(`/v1/erp/connectors/${encodeURIComponent(connectorId)}`, "PATCH", {
          entity_scope: optionalString(input.entity_scope), mapping_entity_name: optionalString(input.mapping_entity_name), mapping_source_schema: optionalString(input.mapping_source_schema),
          mapping_target_schema: optionalString(input.mapping_target_schema), mapping_transform_spec: optionalString(input.mapping_transform_spec), data_classification: optionalString(input.data_classification),
          scope: optionalString(selected.requested_scope), expected_version: optionalNumber(selected.connector_version), idempotency_key: idempotencyKey,
        });
      case "ERP-01-ACT-CONNECTOR-VALIDATE":
        return execute(`/v1/erp/connectors/${encodeURIComponent(connectorId)}/validate`, "POST", { scope: optionalString(selected.requested_scope), expected_version: optionalNumber(selected.connector_version), idempotency_key: idempotencyKey });
      case "ERP-01-ACT-MAPPING-VALIDATE":
        return execute(`/v1/erp/mappings/${encodeURIComponent(connectorId)}/validate`, "POST", { scope: optionalString(selected.requested_scope), expected_version: optionalNumber(selected.mapping_version), idempotency_key: idempotencyKey });
      case "ERP-01-ACT-SNAPSHOT-REFRESH":
        return execute("/v1/erp/snapshots/refresh", "POST", { requested_scope: optionalString(input.requested_scope), scope: optionalString(input.requested_scope), expected_version: optionalNumber(selected.snapshot_version), idempotency_key: idempotencyKey });
      case "ERP-01-ACT-SYNC-CREATE":
        return execute("/v1/erp/sync-jobs", "POST", {
          erp_connector_id: connectorId, requested_scope: optionalString(input.requested_scope), data_classification: optionalString(input.data_classification), records_payload: optionalString(input.records_payload),
          snapshot_type: optionalString(input.snapshot_type), snapshot_document: optionalString(input.snapshot_document), completeness: optionalString(input.completeness),
          external_result_verified: input.external_result_verified === "true" || input.external_result_verified === true, external_evidence_refs: asList(input.external_evidence_refs),
          scope: optionalString(input.requested_scope), expected_version: optionalNumber(selected.connector_version), idempotency_key: idempotencyKey,
        });
      case "ERP-01-ACT-SYNC-STATUS":
        return execute(`/v1/erp/sync-jobs/${encodeURIComponent(jobId)}`, "GET", {});
      case "ERP-01-ACT-SYNC-RETRY":
        return execute(`/v1/erp/sync-jobs/${encodeURIComponent(jobId)}/retry`, "POST", { scope: optionalString(selected.requested_scope), expected_version: optionalNumber(selected.sync_job_version), idempotency_key: idempotencyKey });
      case "ERP-01-ACT-FAILURE-GET":
        return execute(`/v1/erp/failures/${encodeURIComponent(failureId)}`, "GET", {});
      case "ERP-01-ACT-FACTPACK":
        return execute("/v1/erp/finance/fact-pack", "GET", {});
      case "ERP-01-ACT-GUARDRAILS":
        return execute("/v1/erp/capacity/guardrails", "GET", {});
      case "ERP-01-ACT-FORECAST":
        return execute("/v1/erp/forecasts", "GET", {});
      case "ERP-01-ACT-EXPORT":
        return execute("/v1/exports", "POST", { page_uid: "admin:ERP-01", scope: optionalString(input.scope), idempotency_key: idempotencyKey });
      default:
        return { ok: false, error_uid: "ERP-01-ERR-UNDEFINED", reason_code: `ERP_COMMAND_OPERATION_NOT_REGISTERED:${action_uid}`, correlation_id };
    }
  },
});

type Runtime = {
  projection: ErpNormalizedProjection | null;
  setProjection: (value: ErpNormalizedProjection) => void;
  runtimeError: string | null;
  setRuntimeError: (value: string | null) => void;
  correlationId: string | null;
  setCorrelationId: (value: string | null) => void;
  pending: boolean;
  invoke: (actionUid: string, controlUid: string, form?: Readonly<Record<string,unknown>>) => Promise<boolean>;
};

const Ctx = createContext<Runtime | null>(null);

export function ErpRuntimeProvider({ children }: { children: ReactNode }) {
  const [projection, setProjection] = useState<ErpNormalizedProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const syncProjection = async (signal?: AbortSignal) => {
    const result = await readErpProjection(signal);
    setCorrelationId(result.correlation_id);
    if (result.ok) {
      setProjection(result.projection);
      setRuntimeError(null);
    } else {
      setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    void syncProjection(controller.signal);
    return () => controller.abort();
  }, []);

  const invoke = async (actionUid: string, controlUid: string, form?: Readonly<Record<string,unknown>>) => {
    if (!projection) {
      setRuntimeError("ERP-01-ERR-UNDEFINED: ERP_COMMAND_PROJECTION_NOT_READY");
      return false;
    }
    setPending(true);
    try {
      const result = await invokeErpCommand({ action_uid: actionUid, control_uid: controlUid, projection, form });
      setCorrelationId(result.correlation_id);
      if (result.ok) {
        setProjection(result.projection);
        setRuntimeError(null);
        return true;
      }
      setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
      return false;
    } finally {
      setPending(false);
    }
  };

  const value = useMemo(() => ({ projection, setProjection, runtimeError, setRuntimeError, correlationId, setCorrelationId, pending, invoke }), [projection, runtimeError, correlationId, pending]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useErpRuntimeState() {
  const value = useContext(Ctx);
  if (!value) throw new Error("ERP_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

export function ErpValue({ controlId }: { controlId: string }) {
  const { projection } = useErpRuntimeState();
  return <>{projection?.values[controlId] ?? "—"}</>;
}

export function ErpGovernedButton({ controlId, className, children, onUiClick }: { controlId: string; className?: string; children: ReactNode; onUiClick?: () => void }) {
  const runtime = useErpRuntimeState();
  const binding: ErpControlBinding | undefined = ERP_CONTROL_BINDINGS[controlId as ErpControlUid];
  const allowed = Boolean(binding) && runtime.projection?.gate_state[binding.gate_uid] === true;
  const local = binding?.effect_type === "UI_CONTEXT_STATE";
  const enabled = allowed && (local || isErpCommandAdapterBound()) && !runtime.pending;
  const click = () => {
    if (!binding) return;
    if (local) { onUiClick?.(); return; }
    void runtime.invoke(binding.action_uid, controlId);
  };
  return (
    <button type="button" className={className} data-control-id={controlId} data-action-uid={binding?.action_uid} data-gate-uid={binding?.gate_uid} data-permission-uid={binding?.permission_uid}
      data-disabled-reason={!allowed ? binding?.gate_uid : !local && !isErpCommandAdapterBound() ? "ERP_COMMAND_RUNTIME_NOT_BOUND" : undefined} disabled={!enabled} onClick={click}>
      {children}
    </button>
  );
}
