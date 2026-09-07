"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { readSocProjection, type SocNormalizedProjection } from "@/domain/social/socProjectionPort";
import { invokeSocCommand, isSocCommandActionBound } from "@/domain/social/socCommandPort";
import {
  SOC_CONTROL_BINDINGS,
  type SocControlBinding,
  type SocControlUid,
} from "@/domain/social/socControlBindings";
import { ensureControlledSocClientTestRuntime } from "@/domain/social/controlledSocClientTestRuntime";

type Runtime = {
  projection: SocNormalizedProjection | null;
  setProjection: (value: SocNormalizedProjection) => void;
  runtimeError: string | null;
  setRuntimeError: (value: string | null) => void;
  correlationId: string | null;
  setCorrelationId: (value: string | null) => void;
};

const Ctx = createContext<Runtime | null>(null);

export function SocRuntimeProvider({ children }: { children: ReactNode }) {
  ensureControlledSocClientTestRuntime();
  const [projection, setProjection] = useState<SocNormalizedProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void readSocProjection(controller.signal).then((result) => {
      setCorrelationId(result.correlation_id);
      if (result.ok) {
        setProjection(result.projection);
        setRuntimeError(null);
      } else {
        setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
      }
    });
    return () => controller.abort();
  }, []);

  const value = useMemo(
    () => ({ projection, setProjection, runtimeError, setRuntimeError, correlationId, setCorrelationId }),
    [projection, runtimeError, correlationId],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSocRuntimeState() {
  const value = useContext(Ctx);
  if (!value) throw new Error("SOC_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

export function useSocGate(gateUid: string) {
  return useSocRuntimeState().projection?.gate_state[gateUid] === true;
}

export function SocValue({ controlId }: { controlId: string }) {
  const { projection } = useSocRuntimeState();
  return <>{projection?.values[controlId] ?? "—"}</>;
}

function apply(runtime: Runtime, binding: SocControlBinding, controlId: string) {
  void invokeSocCommand({
    action_uid: binding.action_uid,
    control_uid: controlId,
    projection: runtime.projection,
  }).then((result) => {
    runtime.setCorrelationId(result.correlation_id);
    if (result.ok) {
      runtime.setProjection(result.projection);
      runtime.setRuntimeError(null);
    } else {
      runtime.setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
    }
  });
}

export function SocSearchInput({
  controlId,
  className,
  placeholder,
}: {
  controlId: string;
  className?: string;
  placeholder?: string;
}) {
  const runtime = useSocRuntimeState();
  const binding: SocControlBinding | undefined = SOC_CONTROL_BINDINGS[controlId as SocControlUid];
  const allowed = Boolean(binding) && runtime.projection?.gate_state[binding!.gate_uid] === true;
  const commandReady = Boolean(binding) && isSocCommandActionBound(binding!.action_uid);
  const enabled = allowed && commandReady;
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && binding && enabled) {
      event.preventDefault();
      apply(runtime, binding, controlId);
    }
  };
  return (
    <input
      className={className}
      data-control-id={controlId}
      data-action-uid={binding?.action_uid}
      data-gate-uid={binding?.gate_uid}
      data-disabled-reason={!allowed ? binding?.gate_uid : !commandReady ? "SOC_COMMAND_RUNTIME_NOT_BOUND" : undefined}
      placeholder={placeholder}
      disabled={!enabled}
      onKeyDown={onKeyDown}
    />
  );
}

export function SocGovernedButton({
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
  const runtime = useSocRuntimeState();
  const binding: SocControlBinding | undefined = SOC_CONTROL_BINDINGS[controlId as SocControlUid];
  const allowed = Boolean(binding) && runtime.projection?.gate_state[binding!.gate_uid] === true;
  const local = binding?.effect_type === "UI_CONTEXT_STATE" || binding?.effect_type === "UI_ONLY";
  const commandReady = Boolean(binding) && isSocCommandActionBound(binding!.action_uid);
  const enabled = allowed && (local || commandReady);

  const click = () => {
    if (!binding || !enabled) return;
    if (local) {
      onUiClick?.();
      return;
    }
    apply(runtime, binding, controlId);
  };

  return (
    <button
      type="button"
      className={className}
      data-control-id={controlId}
      data-action-uid={binding?.action_uid}
      data-gate-uid={binding?.gate_uid}
      data-permission-uid={binding?.permission_uid}
      data-disabled-reason={!allowed ? binding?.gate_uid : !local && !commandReady ? "SOC_COMMAND_RUNTIME_NOT_BOUND" : undefined}
      disabled={!enabled}
      onClick={click}
    >
      {children}
    </button>
  );
}
