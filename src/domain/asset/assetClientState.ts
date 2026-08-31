import type { AssetNormalizedProjection } from "./assetProjectionPort";

export type AssetMode = "AUTO" | "MANUAL";
export type AssetCompareMode = "SINGLE" | "AB" | "ABC";
export type AssetViewActionUid =
  | "ASSET-01-ACT-BINDING-VIEW"
  | "ASSET-01-ACT-BLUEPRINT-VIEW"
  | "ASSET-01-ACT-SCRIPT-VIEW"
  | "ASSET-01-ACT-RESULT-VIEW"
  | "ASSET-01-ACT-RUNTIME-VIEW"
  | "ASSET-01-ACT-VERSION-HISTORY";

export type AssetClientState = {
  project_ref: string | null;
  topic_ref: string | null;
  asset_ref: string | null;
  mode: AssetMode;
  search: string;
  filter: string | null;
  compare_mode: AssetCompareMode;
  zoom: number;
  reference_overlay: boolean;
  active_view_action: AssetViewActionUid | null;
  correction_open: boolean;
  correction_request: string;
  patch_revision_requested: boolean;
  projection: AssetNormalizedProjection | null;
  correlation_id: string | null;
  runtime_error: string | null;
  busy_action: string | null;
};

export const INITIAL_ASSET_CLIENT_STATE: AssetClientState = {
  project_ref: null,
  topic_ref: null,
  asset_ref: null,
  mode: "AUTO",
  search: "",
  filter: null,
  compare_mode: "SINGLE",
  zoom: 1,
  reference_overlay: false,
  active_view_action: null,
  correction_open: false,
  correction_request: "",
  patch_revision_requested: false,
  projection: null,
  correlation_id: null,
  runtime_error: null,
  busy_action: null,
};

export type AssetClientAction =
  | { action_uid: "ASSET-01-ACT-PROJECT-SELECT"; project_ref: string | null }
  | { action_uid: "ASSET-01-ACT-TOPIC-SELECT"; topic_ref: string | null }
  | { action_uid: "ASSET-01-ACT-MODE-SET"; mode: AssetMode }
  | { action_uid: "ASSET-01-ACT-ASSET-SEARCH"; search: string }
  | { action_uid: "ASSET-01-ACT-ASSET-FILTER"; filter: string | null }
  | { action_uid: "ASSET-01-ACT-ASSET-SELECT"; asset_ref: string | null }
  | { action_uid: "ASSET-01-ACT-COMPARE-SINGLE" }
  | { action_uid: "ASSET-01-ACT-COMPARE-AB" }
  | { action_uid: "ASSET-01-ACT-COMPARE-ABC" }
  | { action_uid: "ASSET-01-ACT-ZOOM-IN" }
  | { action_uid: "ASSET-01-ACT-ZOOM-OUT" }
  | { action_uid: "ASSET-01-ACT-FIT" }
  | { action_uid: "ASSET-01-ACT-REFERENCE-TOGGLE" }
  | { action_uid: AssetViewActionUid }
  | { action_uid: "ASSET-01-ACT-CORRECTION-OPEN" }
  | { action_uid: "ASSET-01-ACT-PATCH-REVISE" }
  | { action_uid: "LOCAL-CORRECTION-REQUEST"; value: string }
  | { action_uid: "PROJECTION"; value: AssetNormalizedProjection; correlation_id: string }
  | { action_uid: "RUNTIME-ERROR"; value: string | null; correlation_id?: string | null }
  | { action_uid: "BUSY"; value: string | null };

function firstRef(projection: AssetNormalizedProjection, id: string) {
  return projection.lists[id]?.[0]?.ref ?? null;
}

export function reduceAssetClientState(state: AssetClientState, action: AssetClientAction): AssetClientState {
  switch (action.action_uid) {
    case "ASSET-01-ACT-PROJECT-SELECT":
      return {
        ...state,
        project_ref: action.project_ref,
        topic_ref: null,
        asset_ref: null,
        active_view_action: null,
        patch_revision_requested: false,
      };
    case "ASSET-01-ACT-TOPIC-SELECT":
      return {
        ...state,
        topic_ref: action.topic_ref,
        asset_ref: null,
        active_view_action: null,
        patch_revision_requested: false,
      };
    case "ASSET-01-ACT-MODE-SET":
      return { ...state, mode: action.mode };
    case "ASSET-01-ACT-ASSET-SEARCH":
      return { ...state, search: action.search };
    case "ASSET-01-ACT-ASSET-FILTER":
      return { ...state, filter: action.filter };
    case "ASSET-01-ACT-ASSET-SELECT":
      return {
        ...state,
        asset_ref: action.asset_ref,
        active_view_action: null,
        patch_revision_requested: false,
      };
    case "ASSET-01-ACT-COMPARE-SINGLE":
      return { ...state, compare_mode: "SINGLE" };
    case "ASSET-01-ACT-COMPARE-AB":
      return { ...state, compare_mode: "AB" };
    case "ASSET-01-ACT-COMPARE-ABC":
      return { ...state, compare_mode: "ABC" };
    case "ASSET-01-ACT-ZOOM-IN":
      return { ...state, zoom: Math.min(8, state.zoom + 0.25) };
    case "ASSET-01-ACT-ZOOM-OUT":
      return { ...state, zoom: Math.max(0.25, state.zoom - 0.25) };
    case "ASSET-01-ACT-FIT":
      return { ...state, zoom: 1 };
    case "ASSET-01-ACT-REFERENCE-TOGGLE":
      return { ...state, reference_overlay: !state.reference_overlay };
    case "ASSET-01-ACT-BINDING-VIEW":
    case "ASSET-01-ACT-BLUEPRINT-VIEW":
    case "ASSET-01-ACT-SCRIPT-VIEW":
    case "ASSET-01-ACT-RESULT-VIEW":
    case "ASSET-01-ACT-RUNTIME-VIEW":
    case "ASSET-01-ACT-VERSION-HISTORY":
      return { ...state, active_view_action: action.action_uid };
    case "ASSET-01-ACT-CORRECTION-OPEN":
      return { ...state, correction_open: true };
    case "ASSET-01-ACT-PATCH-REVISE":
      return { ...state, patch_revision_requested: true };
    case "LOCAL-CORRECTION-REQUEST":
      return { ...state, correction_request: action.value };
    case "PROJECTION": {
      const correction_open =
        action.value.page_state === "CORRECTION_REQUIRED"
          ? true
          : action.value.page_state === "WAIT_CONFIRMATION"
            ? state.correction_open
            : false;
      return {
        ...state,
        projection: action.value,
        project_ref: state.project_ref ?? firstRef(action.value, "ASSET-01-CTL-PROJECT"),
        topic_ref: state.topic_ref ?? firstRef(action.value, "ASSET-01-CTL-TOPIC"),
        correction_open,
        correlation_id: action.correlation_id,
        runtime_error: null,
      };
    }
    case "RUNTIME-ERROR":
      return {
        ...state,
        runtime_error: action.value,
        correlation_id: action.correlation_id === undefined ? state.correlation_id : action.correlation_id,
      };
    case "BUSY":
      return { ...state, busy_action: action.value };
  }
}
