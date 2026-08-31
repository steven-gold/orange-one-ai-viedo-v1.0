"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { assetText } from "@/i18n/assetCatalog";
import { ASSET_CONTROL_BINDINGS, type AssetControlUid } from "@/domain/asset/assetControlBindings";
import {
  INITIAL_ASSET_CLIENT_STATE,
  reduceAssetClientState,
  type AssetClientAction,
  type AssetClientState,
  type AssetViewActionUid,
} from "@/domain/asset/assetClientState";
import { readAssetProjection, type AssetNormalizedProjection } from "@/domain/asset/assetProjectionPort";
import { buildAndInvokeAssetAction, isAssetRequestBuilderBound } from "@/domain/asset/assetRequestAdapter";
import { rememberControlledAssetProjection } from "@/domain/asset/controlledAssetClientTestRuntime";
import type { AssetActionUid } from "@/domain/asset/assetRuntimeContract";
import styles from "./AssetVisual.module.css";

export type AssetVisualControlKind = "readonly" | "button" | "primary" | "select" | "search" | "segmented" | "list";

type Runtime = {
  state: AssetClientState;
  dispatch: Dispatch<AssetClientAction>;
};

const Ctx = createContext<Runtime | null>(null);

const VIEW_COMPONENT: Record<AssetViewActionUid, string> = {
  "ASSET-01-ACT-BINDING-VIEW": "ASSET-01-CMP-BINDING",
  "ASSET-01-ACT-BLUEPRINT-VIEW": "ASSET-01-CMP-BINDING",
  "ASSET-01-ACT-SCRIPT-VIEW": "ASSET-01-CMP-SCRIPT",
  "ASSET-01-ACT-RESULT-VIEW": "ASSET-01-CMP-SCORE",
  "ASSET-01-ACT-RUNTIME-VIEW": "ASSET-01-CMP-RUNTIME",
  "ASSET-01-ACT-VERSION-HISTORY": "ASSET-01-CMP-VERSION",
};

async function syncProjection(dispatch: Dispatch<AssetClientAction>) {
  const result = await readAssetProjection();
  if (result.ok) {
    rememberControlledAssetProjection(result.projection);
    dispatch({ action_uid: "PROJECTION", value: result.projection, correlation_id: result.correlation_id });
    return true;
  }
  dispatch({
    action_uid: "RUNTIME-ERROR",
    value: `${result.error_uid}: ${result.reason_code}`,
    correlation_id: result.correlation_id,
  });
  return false;
}

export function AssetRuntimeProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reduceAssetClientState, INITIAL_ASSET_CLIENT_STATE);

  useEffect(() => {
    const controller = new AbortController();
    void readAssetProjection(controller.signal).then((result) => {
      if (result.ok) {
        rememberControlledAssetProjection(result.projection);
        dispatch({ action_uid: "PROJECTION", value: result.projection, correlation_id: result.correlation_id });
      } else {
        dispatch({
          action_uid: "RUNTIME-ERROR",
          value: `${result.error_uid}: ${result.reason_code}`,
          correlation_id: result.correlation_id,
        });
      }
    });
    return () => controller.abort();
  }, []);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAssetRuntimeState() {
  const value = useContext(Ctx);
  if (!value) throw new Error("ASSET_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

function gate(state: AssetClientState, uid: string) {
  return state.projection?.gate_state[uid] === true;
}

function displayValue(id: string, state: AssetClientState) {
  if (id === "ASSET-01-FLD-TRACE") return state.runtime_error ?? state.correlation_id ?? "—";
  if (id === "ASSET-01-FLD-TASK") return state.projection?.task_id ?? "—";
  if (id === "ASSET-01-FLD-OUTPUT-ID") return state.projection?.output_version_id ?? "—";
  return state.projection?.values[id] ?? "—";
}

function listItems(id: string, state: AssetClientState) {
  return state.projection?.lists[id] ?? [];
}

function filterItems(id: string, state: AssetClientState) {
  return state.projection?.filters[id] ?? state.projection?.lists[id] ?? [];
}

const LOCAL = new Set<AssetActionUid>([
  "ASSET-01-ACT-PROJECT-SELECT",
  "ASSET-01-ACT-TOPIC-SELECT",
  "ASSET-01-ACT-MODE-SET",
  "ASSET-01-ACT-ASSET-SEARCH",
  "ASSET-01-ACT-ASSET-FILTER",
  "ASSET-01-ACT-ASSET-SELECT",
  "ASSET-01-ACT-BLUEPRINT-VIEW",
  "ASSET-01-ACT-SCRIPT-VIEW",
  "ASSET-01-ACT-BINDING-VIEW",
  "ASSET-01-ACT-COMPARE-SINGLE",
  "ASSET-01-ACT-COMPARE-AB",
  "ASSET-01-ACT-COMPARE-ABC",
  "ASSET-01-ACT-ZOOM-IN",
  "ASSET-01-ACT-ZOOM-OUT",
  "ASSET-01-ACT-FIT",
  "ASSET-01-ACT-REFERENCE-TOGGLE",
  "ASSET-01-ACT-RESULT-VIEW",
  "ASSET-01-ACT-CORRECTION-OPEN",
  "ASSET-01-ACT-RUNTIME-VIEW",
  "ASSET-01-ACT-VERSION-HISTORY",
  "ASSET-01-ACT-PATCH-REVISE",
]);

function focusExistingComponent(componentUid: string) {
  requestAnimationFrame(() => {
    document
      .querySelector<HTMLElement>(`[data-component-uid="${componentUid}"]`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function dispatchViewAction(action: AssetViewActionUid, dispatch: Dispatch<AssetClientAction>) {
  dispatch({ action_uid: action });
  focusExistingComponent(VIEW_COMPONENT[action]);
}

function localDispatch(
  action: AssetActionUid,
  value: unknown,
  dispatch: Dispatch<AssetClientAction>,
) {
  switch (action) {
    case "ASSET-01-ACT-PROJECT-SELECT":
      dispatch({ action_uid: action, project_ref: typeof value === "string" && value ? value : null });
      return;
    case "ASSET-01-ACT-TOPIC-SELECT":
      dispatch({ action_uid: action, topic_ref: typeof value === "string" && value ? value : null });
      return;
    case "ASSET-01-ACT-MODE-SET":
      if (value === "AUTO" || value === "MANUAL") dispatch({ action_uid: action, mode: value });
      return;
    case "ASSET-01-ACT-ASSET-SEARCH":
      dispatch({ action_uid: action, search: String(value ?? "") });
      return;
    case "ASSET-01-ACT-ASSET-FILTER":
      dispatch({ action_uid: action, filter: typeof value === "string" && value ? value : null });
      return;
    case "ASSET-01-ACT-ASSET-SELECT":
      dispatch({ action_uid: action, asset_ref: typeof value === "string" && value ? value : null });
      return;
    case "ASSET-01-ACT-COMPARE-SINGLE":
    case "ASSET-01-ACT-COMPARE-AB":
    case "ASSET-01-ACT-COMPARE-ABC":
    case "ASSET-01-ACT-ZOOM-IN":
    case "ASSET-01-ACT-ZOOM-OUT":
    case "ASSET-01-ACT-FIT":
    case "ASSET-01-ACT-REFERENCE-TOGGLE":
    case "ASSET-01-ACT-CORRECTION-OPEN":
      dispatch({ action_uid: action });
      return;
    case "ASSET-01-ACT-BINDING-VIEW":
    case "ASSET-01-ACT-BLUEPRINT-VIEW":
    case "ASSET-01-ACT-SCRIPT-VIEW":
    case "ASSET-01-ACT-RESULT-VIEW":
    case "ASSET-01-ACT-RUNTIME-VIEW":
    case "ASSET-01-ACT-VERSION-HISTORY":
      dispatchViewAction(action, dispatch);
      return;
    case "ASSET-01-ACT-PATCH-REVISE":
      dispatch({ action_uid: action });
      focusExistingComponent("ASSET-01-CMP-PATCH");
      return;
  }
}

function projectionFromResult(value: unknown): AssetNormalizedProjection | null {
  if (!value || typeof value !== "object") return null;
  const projection = (value as { projection?: unknown }).projection;
  return projection && typeof projection === "object" ? (projection as AssetNormalizedProjection) : null;
}

async function formalInvoke(
  control_uid: string,
  action_uid: AssetActionUid,
  control_value: unknown,
  state: AssetClientState,
  dispatch: Dispatch<AssetClientAction>,
) {
  dispatch({ action_uid: "BUSY", value: action_uid });
  rememberControlledAssetProjection(state.projection);
  try {
    const result = await buildAndInvokeAssetAction({
      control_uid,
      control_value,
      action_uid,
      state,
      projection: state.projection,
      correction_request: state.correction_request,
    });
    if (!result.ok) {
      dispatch({
        action_uid: "RUNTIME-ERROR",
        value: `${result.error_uid}: ${result.reason_code}`,
        correlation_id: result.correlation_id,
      });
      return;
    }

    const embedded = projectionFromResult(result.value);
    if (embedded) {
      rememberControlledAssetProjection(embedded);
      dispatch({ action_uid: "PROJECTION", value: embedded, correlation_id: result.correlation_id });
      return;
    }
    await syncProjection(dispatch);
  } finally {
    dispatch({ action_uid: "BUSY", value: null });
  }
}

export function AssetRuntimeControl({ id, kind }: { id: string; kind: AssetVisualControlKind }) {
  const { state, dispatch } = useAssetRuntimeState();
  const { locale } = useI18n();
  const binding = ASSET_CONTROL_BINDINGS[id as AssetControlUid];
  const label = assetText(locale, id);
  const allowed = Boolean(binding) && gate(state, binding.gate_uid);
  const action = binding?.action_uid as AssetActionUid | undefined;
  const local = Boolean(action && LOCAL.has(action));
  const formal = Boolean(action && !LOCAL.has(action));
  const builderReady = !formal || isAssetRequestBuilderBound();
  const enabled = Boolean(binding && action);
  const busy = state.busy_action !== null;
  const common = {
    "data-control-id": id,
    "data-action-uid": binding?.action_uid,
    "data-gate-uid": binding?.gate_uid,
    "data-permission-uid": binding?.permission_uid,
    "data-effect-type": binding?.effect_type,
    "data-binding-kind": binding?.binding_kind,
    "data-busy-action": state.busy_action ?? undefined,
    "data-disabled-reason":
      !binding || !action
        ? "NO_ACTION_BINDING"
        : !allowed
          ? binding.gate_uid
          : !builderReady
            ? "ASSET_REQUEST_ADAPTER_NOT_BOUND"
            : busy
              ? "BUSY"
              : undefined,
  };

  const block = (reason: string) =>
    dispatch({ action_uid: "RUNTIME-ERROR", value: `ASSET-01-ERR-CONTEXT-001: ${reason}` });

  const act = (value?: unknown) => {
    if (!binding || !action) {
      block("ACTION_BINDING_MISSING");
      return;
    }
    if (busy) {
      block(`BUSY:${state.busy_action}`);
      return;
    }
    if (!allowed) {
      block(state.runtime_error ?? `${binding.gate_uid}:NOT_SATISFIED`);
      return;
    }
    if (formal && !builderReady) {
      block("ASSET_REQUEST_ADAPTER_NOT_BOUND");
      return;
    }
    if (local) {
      localDispatch(action, value, dispatch);
      dispatch({ action_uid: "RUNTIME-ERROR", value: null });
      return;
    }
    void formalInvoke(id, action, value, state, dispatch);
  };

  if (kind === "readonly") {
    return (
      <div className={styles.readonly} {...common}>
        <span>{label}</span>
        <strong>{displayValue(id, state)}</strong>
      </div>
    );
  }

  if (kind === "list") {
    const items = listItems(id, state);
    return (
      <div className={styles.listControl} {...common}>
        <span>{label}</span>
        <div className={styles.emptyBox}>
          {items.length
            ? items.map((item) => (
                <button key={item.ref} type="button" disabled={!enabled || busy} onClick={() => act(item.ref)}>
                  {item.label}
                </button>
              ))
            : "—"}
        </div>
      </div>
    );
  }

  if (kind === "segmented") {
    return (
      <div className={styles.segmented} {...common} aria-label={label}>
        <button
          type="button"
          disabled={!enabled || busy}
          className={state.mode === "AUTO" ? styles.segmentActive : undefined}
          onClick={() => act("AUTO")}
        >
          AUTO
        </button>
        <button
          type="button"
          disabled={!enabled || busy}
          className={state.mode === "MANUAL" ? styles.segmentActive : undefined}
          onClick={() => act("MANUAL")}
        >
          MANUAL
        </button>
      </div>
    );
  }

  if (kind === "search") {
    const correction = id === "ASSET-01-TXT-CORRECTION-REQUEST";
    const value = correction ? state.correction_request : state.search;
    return (
      <label className={styles.inputControl}>
        <span>{label}</span>
        <input
          {...common}
          disabled={!enabled || busy}
          value={value}
          onChange={(event) => {
            if (!allowed) {
              block(state.runtime_error ?? `${binding?.gate_uid ?? "GATE"}:NOT_SATISFIED`);
              return;
            }
            correction
              ? dispatch({ action_uid: "LOCAL-CORRECTION-REQUEST", value: event.target.value })
              : act(event.target.value);
          }}
          placeholder="—"
        />
      </label>
    );
  }

  if (kind === "select") {
    const items = filterItems(id, state);
    const value =
      id === "ASSET-01-CTL-PROJECT"
        ? state.project_ref ?? ""
        : id === "ASSET-01-CTL-TOPIC"
          ? state.topic_ref ?? ""
          : id === "ASSET-01-CTL-FILTER"
            ? state.filter ?? ""
            : "";
    return (
      <label className={styles.inputControl}>
        <span>{label}</span>
        <select
          {...common}
          disabled={!enabled || busy}
          value={value}
          onClick={() => !allowed && block(state.runtime_error ?? `${binding?.gate_uid ?? "GATE"}:NOT_SATISFIED`)}
          onChange={(event) => act(event.target.value)}
        >
          <option value="">—</option>
          {items.map((item) => (
            <option key={item.ref} value={item.ref}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <button
      {...common}
      type="button"
      disabled={!enabled || busy}
      onClick={() => act()}
      className={`${styles.button} ${kind === "primary" ? styles.primary : ""}`}
    >
      {label}
    </button>
  );
}
