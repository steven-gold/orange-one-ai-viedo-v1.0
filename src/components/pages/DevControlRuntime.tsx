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
  isDevProjectionResolverBound,
  readDevProjection,
  type DevNormalizedProjection,
} from "@/domain/dev/devProjectionPort";
import {
  invokeDevCommand,
  isDevCommandAdapterBound,
} from "@/domain/dev/devCommandPort";
import {
  DEV_CONTROL_BINDINGS,
  type DevControlBinding,
  type DevControlUid,
} from "@/domain/dev/devControlBindings";
import { ensureControlledDevClientTestRuntime } from "@/domain/dev/controlledDevClientTestRuntime";
import type { DevGateUid } from "@/domain/dev/devRuntimeContract";

type ProjectionStatus = "LOADING" | "READY" | "BLOCKED";

type Runtime = {
  projection: DevNormalizedProjection | null;
  setProjection: (value: DevNormalizedProjection) => void;
  projectionStatus: ProjectionStatus;
  runtimeErrorUid: string | null;
  runtimeReason: string | null;
  setRuntimeFailure: (errorUid: string | null, reason: string | null) => void;
  correlationId: string | null;
  setCorrelationId: (value: string | null) => void;
  projectionAdapterReady: boolean;
  commandAdapterReady: boolean;
  effectfulRuntimeReady: boolean;
};

const Ctx = createContext<Runtime | null>(null);

export function DevRuntimeProvider({ children }: { children: ReactNode }) {
  ensureControlledDevClientTestRuntime();
  const [projection, setProjection] = useState<DevNormalizedProjection | null>(null);
  const [projectionStatus, setProjectionStatus] = useState<ProjectionStatus>("LOADING");
  const [runtimeErrorUid, setRuntimeErrorUid] = useState<string | null>(null);
  const [runtimeReason, setRuntimeReason] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const projectionAdapterReady = isDevProjectionResolverBound();
  const commandAdapterReady = isDevCommandAdapterBound();

  const setRuntimeFailure = (errorUid: string | null, reason: string | null) => {
    setRuntimeErrorUid(errorUid);
    setRuntimeReason(reason);
  };

  useEffect(() => {
    const controller = new AbortController();
    void readDevProjection(controller.signal).then((result) => {
      setCorrelationId(result.correlation_id);
      if (result.ok) {
        setProjection(result.projection);
        setProjectionStatus("READY");
        setRuntimeFailure(null, null);
      } else {
        setProjectionStatus("BLOCKED");
        setRuntimeFailure(result.error_uid, result.reason_code);
      }
    });
    return () => controller.abort();
  }, []);

  const effectfulRuntimeReady = projectionStatus === "READY" && projectionAdapterReady && commandAdapterReady;

  const value = useMemo(
    () => ({
      projection,
      setProjection,
      projectionStatus,
      runtimeErrorUid,
      runtimeReason,
      setRuntimeFailure,
      correlationId,
      setCorrelationId,
      projectionAdapterReady,
      commandAdapterReady,
      effectfulRuntimeReady,
    }),
    [
      projection,
      projectionStatus,
      runtimeErrorUid,
      runtimeReason,
      correlationId,
      projectionAdapterReady,
      commandAdapterReady,
      effectfulRuntimeReady,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDevRuntimeState() {
  const value = useContext(Ctx);
  if (!value) throw new Error("DEV_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

export function useDevGate(gateUid: DevGateUid) {
  const { projection } = useDevRuntimeState();
  return projection?.gate_state[gateUid] === true;
}

export function DevGovernedButton({
  controlId,
  className,
  children,
  onUiClick,
}: {
  controlId: string;
  className?: string;
  children: ReactNode;
  onUiClick?: () => void;
}) {
  const runtime = useDevRuntimeState();
  const binding: DevControlBinding | undefined = DEV_CONTROL_BINDINGS[controlId as DevControlUid];
  const allowed = Boolean(binding) && runtime.projection?.gate_state[binding!.gate_uid as DevGateUid] === true;
  const formal = binding?.effect_type !== "UI_CONTEXT_STATE";
  const formalRuntimeReady = formal ? runtime.commandAdapterReady : true;
  const enabled = Boolean(binding) && allowed && formalRuntimeReady;

  const disabledReason = !binding
    ? "DEV-01-ERR-UNDEFINED"
    : !allowed
      ? binding.gate_uid
      : formal && !runtime.commandAdapterReady
        ? "DEV_COMMAND_RUNTIME_NOT_BOUND"
        : undefined;

  const click = () => {
    if (!binding || !enabled) return;
    if (!formal) {
      onUiClick?.();
      return;
    }
    void invokeDevCommand({
      action_uid: binding.action_uid,
      control_uid: controlId,
      projection: runtime.projection,
    }).then((result) => {
      runtime.setCorrelationId(result.correlation_id);
      if (result.ok) {
        runtime.setProjection(result.projection);
        runtime.setRuntimeFailure(null, null);
      } else {
        runtime.setRuntimeFailure(result.error_uid, result.reason_code);
      }
    });
  };

  return (
    <button
      className={className}
      type="button"
      data-control-id={controlId}
      data-action-uid={binding?.action_uid}
      data-gate-uid={binding?.gate_uid}
      data-permission-uid={binding?.permission}
      data-effect-type={binding?.effect_type}
      data-runtime-binding={binding?.runtime_binding}
      data-operation={binding?.operation}
      data-method-path={binding?.method_path}
      data-current-state={enabled ? "ENABLED" : "DISABLED"}
      data-formal-runtime-ready={formal ? String(runtime.commandAdapterReady) : "not-required"}
      data-disabled-reason={disabledReason}
      disabled={!enabled}
      onClick={click}
    >
      {children}
    </button>
  );
}
