"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  INITIAL_IAM_CLIENT_STATE,
  openIamCreate,
  openIamEdit,
  selectAllAdmin,
  selectAllFront,
  type IamClientState,
} from "@/domain/iam/iamClientState";
import {
  invokeIamClientCommand,
  isIamClientCommandAdapterBound,
  isIamProjectionResolverBound,
  readIamProjection,
  type IamNormalizedProjection,
} from "@/domain/iam/iamClientPort";
import { ensureControlledIamClientTestRuntime } from "@/domain/iam/controlledIamClientTestRuntime";
import {
  IAM_CONTROL_BINDINGS,
  type IamControlBinding,
  type IamControlUid,
} from "@/domain/iam/iamControlBindings";
import type { IamPageState } from "@/domain/iam/iamRuntimeContract";

export type IamRuntime = {
  client: IamClientState;
  setClient: (value: IamClientState) => void;
  projection: IamNormalizedProjection | null;
  setProjection: (value: IamNormalizedProjection) => void;
  runtimeError: string | null;
  runtimeErrorUid: string | null;
  runtimeReasonCode: string | null;
  correlationId: string | null;
  setRuntimeFailure: (errorUid: string, reasonCode: string, correlationId: string) => void;
  clearRuntimeFailure: () => void;
  setCorrelationId: (value: string | null) => void;
};

const Ctx = createContext<IamRuntime | null>(null);

export function IamRuntimeProvider({ children }: { children: ReactNode }) {
  ensureControlledIamClientTestRuntime();
  const [client, setClient] = useState<IamClientState>(INITIAL_IAM_CLIENT_STATE);
  const [projection, setProjection] = useState<IamNormalizedProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [runtimeErrorUid, setRuntimeErrorUid] = useState<string | null>(null);
  const [runtimeReasonCode, setRuntimeReasonCode] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);

  const setRuntimeFailure = (errorUid: string, reasonCode: string, nextCorrelationId: string) => {
    setRuntimeErrorUid(errorUid);
    setRuntimeReasonCode(reasonCode);
    setRuntimeError(`${errorUid}: ${reasonCode}`);
    setCorrelationId(nextCorrelationId);
  };

  const clearRuntimeFailure = () => {
    setRuntimeErrorUid(null);
    setRuntimeReasonCode(null);
    setRuntimeError(null);
  };

  useEffect(() => {
    const controller = new AbortController();
    void readIamProjection(controller.signal).then((result) => {
      setCorrelationId(result.correlation_id);
      if (result.ok) {
        setProjection(result.projection);
        clearRuntimeFailure();
      } else {
        setRuntimeFailure(result.error_uid, result.reason_code, result.correlation_id);
      }
    });
    return () => controller.abort();
  }, []);

  const value = useMemo<IamRuntime>(
    () => ({
      client,
      setClient,
      projection,
      setProjection,
      runtimeError,
      runtimeErrorUid,
      runtimeReasonCode,
      correlationId,
      setRuntimeFailure,
      clearRuntimeFailure,
      setCorrelationId,
    }),
    [client, projection, runtimeError, runtimeErrorUid, runtimeReasonCode, correlationId],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useIamRuntimeState() {
  const value = useContext(Ctx);
  if (!value) throw new Error("IAM_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

export function useIamGate(gateUid: string) {
  return useIamRuntimeState().projection?.gate_state[gateUid] === true;
}

function toggle(list: string[], key: string, on: boolean) {
  return on ? [...new Set([...list, key])] : list.filter((item) => item !== key);
}

export function setIamFrontL1(runtime: IamRuntime, key: string, on: boolean) {
  runtime.setClient({ ...runtime.client, front_l1: toggle(runtime.client.front_l1, key, on) });
}

export function setIamAdminL1(runtime: IamRuntime, key: string, on: boolean) {
  runtime.setClient({ ...runtime.client, admin_l1: toggle(runtime.client.admin_l1, key, on) });
}

export function setIamBasicField(runtime: IamRuntime, key: string, value: string) {
  runtime.setClient({ ...runtime.client, basic_data: { ...runtime.client.basic_data, [key]: value } });
}

export function setIamSearchQuery(runtime: IamRuntime, value: string) {
  runtime.setClient({ ...runtime.client, search_query: value });
}

export function selectIamAccount(runtime: IamRuntime, accountId: string) {
  runtime.setClient({ ...runtime.client, account_id: accountId });
}

export function setIamDepartmentPreset(runtime: IamRuntime, presetRef: string | null) {
  if (!presetRef) {
    runtime.setClient({ ...runtime.client, department_preset_ref: null });
    return;
  }
  const preset = runtime.projection?.department_presets.find((item) => item.ref === presetRef);
  if (!preset) return;
  runtime.setClient({
    ...runtime.client,
    department_preset_ref: preset.ref,
    front_l1: [...preset.front_l1],
    admin_l1: [...preset.admin_l1],
  });
}

export function getIamPageState(runtime: IamRuntime): IamPageState {
  if (runtime.runtimeReasonCode) return runtime.runtimeReasonCode.includes("FAILED") ? "ERROR" : "BLOCKED";
  if (runtime.client.flow !== "LIST" && runtime.projection?.page_state === "LIST") return runtime.client.flow;
  return runtime.projection?.page_state ?? runtime.client.flow;
}

export function getIamControlRuntime(runtime: IamRuntime, controlId: string) {
  const binding: IamControlBinding | undefined = IAM_CONTROL_BINDINGS[controlId as IamControlUid];
  const gateAllowed = Boolean(binding) && runtime.projection?.gate_state[binding.gate_uid] === true;
  const local = binding?.effect_type === "UI_ONLY" || binding?.effect_type === "DRAFT_UI";
  const readUi = binding?.effect_type === "READ_UI";
  const commandReady = isIamClientCommandAdapterBound();
  const projectionReady = isIamProjectionResolverBound();
  const runtimeReady = local || (readUi ? projectionReady : commandReady);
  const enabled = Boolean(binding) && gateAllowed && runtimeReady;
  return {
    binding,
    gateAllowed,
    local,
    readUi,
    commandReady,
    projectionReady,
    enabled,
    runtimeBinding: local ? "LOCAL_UI" : readUi ? (projectionReady ? "BOUND" : "NOT_EXECUTED") : commandReady ? "BOUND" : "NOT_EXECUTED",
    disabledReason: !binding
      ? "IAM-01-ERR-UNDEFINED"
      : !gateAllowed
        ? binding.gate_uid
        : !runtimeReady
          ? readUi ? "IAM_PROJECTION_ADAPTER_NOT_BOUND" : "IAM_CLIENT_COMMAND_RUNTIME_NOT_BOUND"
          : null,
  } as const;
}

export async function refreshIamProjection(runtime: IamRuntime) {
  const result = await readIamProjection();
  runtime.setCorrelationId(result.correlation_id);
  if (result.ok) {
    runtime.setProjection(result.projection);
    runtime.clearRuntimeFailure();
    return true;
  }
  runtime.setRuntimeFailure(result.error_uid, result.reason_code, result.correlation_id);
  return false;
}

export async function invokeIamControl(runtime: IamRuntime, controlId: string, explicitConfirmation = false) {
  const state = getIamControlRuntime(runtime, controlId);
  const binding = state.binding;
  if (!binding || !state.enabled || state.local || state.readUi) return false;
  const result = await invokeIamClientCommand({
    action_uid: binding.action_uid,
    control_uid: controlId,
    client_state: runtime.client,
    projection: runtime.projection,
    explicit_confirmation: explicitConfirmation,
  });
  runtime.setCorrelationId(result.correlation_id);
  if (result.ok) {
    runtime.setProjection(result.projection);
    runtime.clearRuntimeFailure();
    if (result.client_state && typeof result.client_state === "object") runtime.setClient(result.client_state as IamClientState);
    return true;
  }
  runtime.setRuntimeFailure(result.error_uid, result.reason_code, result.correlation_id);
  return false;
}

export function IamGovernedButton({
  controlId,
  className,
  children,
  selectedAccountId,
  confirmationMessage,
}: {
  controlId: string;
  className?: string;
  children: ReactNode;
  selectedAccountId?: string | null;
  confirmationMessage?: string;
}) {
  const runtime = useIamRuntimeState();
  const state = getIamControlRuntime(runtime, controlId);
  const binding = state.binding;

  const click = () => {
    if (!binding || !state.enabled) return;
    switch (binding.action_uid) {
      case "IAM-01-ACT-OPEN-CREATE":
        runtime.setClient(openIamCreate(runtime.client));
        return;
      case "IAM-01-ACT-OPEN-EDIT": {
        if (!selectedAccountId) return;
        const account = runtime.projection?.accounts.find((item) => item.account_id === selectedAccountId);
        runtime.setClient(openIamEdit(runtime.client, selectedAccountId, {
          front_l1: account?.front_l1,
          admin_l1: account?.admin_l1,
          basic_data: account?.basic_data,
        }));
        return;
      }
      case "IAM-01-ACT-FRONT-ALL-DRAFT":
        runtime.setClient(selectAllFront(runtime.client, runtime.client.front_l1.length !== 9));
        return;
      case "IAM-01-ACT-BACK-ALL-DRAFT":
        runtime.setClient(selectAllAdmin(runtime.client, runtime.client.admin_l1.length !== 9));
        return;
      case "IAM-01-ACT-AUDIT-OPEN":
        runtime.setClient({ ...runtime.client, audit_open: !runtime.client.audit_open });
        void refreshIamProjection(runtime);
        return;
      case "IAM-01-ACT-COMPLETE":
        if (!confirmationMessage || !window.confirm(confirmationMessage)) return;
        void invokeIamControl(runtime, controlId, true);
        return;
    }
    if (state.local || state.readUi) return;
    void invokeIamControl(runtime, controlId);
  };

  return (
    <button
      type="button"
      className={className}
      data-control-id={controlId}
      data-action-uid={binding?.action_uid}
      data-gate-uid={binding?.gate_uid}
      data-permission-uid={binding?.permission}
      data-effect-type={binding?.effect_type}
      data-operation={binding?.operation ?? undefined}
      data-method-path={binding?.method_path ?? undefined}
      data-operations={binding?.operations?.join("|")}
      data-current-state={getIamPageState(runtime)}
      data-runtime-binding={state.runtimeBinding}
      data-gate-allowed={state.gateAllowed ? "true" : "false"}
      data-disabled-reason={state.disabledReason ?? undefined}
      disabled={!state.enabled}
      onClick={click}
    >
      {children}
    </button>
  );
}

export function isIamProjectionRuntimeReady() {
  return isIamProjectionResolverBound();
}

export function isIamEffectfulRuntimeReady() {
  return isIamProjectionResolverBound() && isIamClientCommandAdapterBound();
}
