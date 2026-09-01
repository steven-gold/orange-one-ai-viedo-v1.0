"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  isStrategyAdminCommandAdapterBound,
  invokeStrategyAdminAction,
  readStrategyAdminProjection,
  type StrategyAdminMappedAction,
  type StrategyAdminProjection,
  type StrategyAdminView,
} from "@/domain/strategyAdmin/strategyAdminRuntimePort";

type Runtime = {
  projection: StrategyAdminProjection | null;
  runtimeError: string | null;
  invoke: (actionId: string, view: StrategyAdminView) => Promise<void>;
  canInvoke: (actionId: string) => boolean;
};

const Ctx = createContext<Runtime | null>(null);

const ACTIONS: Readonly<Record<StrategyAdminMappedAction, true>> = {
  "ACT-REFRESH": true,
  "ACT-SEARCH": true,
  "ACT-CONFIGURE": true,
  "ACT-APPROVE": true,
  "ACT-EXPORT": true,
  "ACT-DRAFT-SAVE": true,
  "ACT-CANDIDATE-CREATE": true,
  "ACT-CANDIDATE-COMPARE": true,
  "ACT-ADOPT-CONTEXT": true,
};

export function StrategyAdminRuntimeProvider({ children }: { children: ReactNode }) {
  const [projection, setProjection] = useState<StrategyAdminProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);

  const refreshProjection = useCallback(async (signal?: AbortSignal) => {
    const result = await readStrategyAdminProjection(signal);
    if (!result.ok) {
      setRuntimeError(result.reason_code);
      return false;
    }
    setProjection(result.projection);
    setRuntimeError(null);
    return true;
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshProjection(controller.signal);
    return () => controller.abort();
  }, [refreshProjection]);

  const canInvoke = useCallback(
    (actionId: string) =>
      Boolean(projection?.action_enabled[actionId]) &&
      actionId !== "ACT-CANDIDATE-DECIDE" &&
      actionId !== "ACT-NAV-OPEN" &&
      actionId in ACTIONS &&
      isStrategyAdminCommandAdapterBound(),
    [projection],
  );

  const invoke = useCallback(
    async (actionId: string, view: StrategyAdminView) => {
      if (!projection) {
        setRuntimeError("STR_ADMIN_PROJECTION_NOT_READY");
        return;
      }

      if (actionId === "ACT-CANDIDATE-DECIDE") {
        setRuntimeError(
          "STR_ADMIN_AUTHORITY_BINDING_UNRESOLVED: ACT-CANDIDATE-DECIDE",
        );
        return;
      }

      if (!(actionId in ACTIONS)) {
        setRuntimeError("STR_ADMIN_ACTION_OPERATION_NOT_REGISTERED");
        return;
      }

      const result = await invokeStrategyAdminAction(
        actionId as StrategyAdminMappedAction,
        view,
        projection,
      );

      if (!result.ok) {
        setRuntimeError(result.reason_code);
        return;
      }

      await refreshProjection();
    },
    [projection, refreshProjection],
  );

  const value = useMemo(
    () => ({ projection, runtimeError, invoke, canInvoke }),
    [projection, runtimeError, invoke, canInvoke],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStrategyAdminRuntime() {
  const value = useContext(Ctx);
  if (!value) throw new Error("STRATEGY_ADMIN_RUNTIME_PROVIDER_REQUIRED");
  return value;
}
