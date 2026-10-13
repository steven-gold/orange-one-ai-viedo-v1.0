"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { AssetClientError, fetchAssetReadModel, postAssetAction, type AssetFieldValue } from "@/lib/client";
import { previewAssetAction, usableList } from "@/lib/assetActionPreview";
import { displayAssetValue } from "./assetFormat";
import {
  ASSET_BINDING_FIELDS,
  ASSET_CONTROL_ACTIONS,
  ASSET_HANDOFF_FIELDS,
  ASSET_REUSE_FIELDS,
  ASSET_RUNTIME_FIELDS,
  ASSET_SCORE_FIELDS,
  ASSET_VISIBLE_CONTROLS,
} from "./assetControls";
import styles from "./AssetVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type NameDialogKind = "project" | "topic" | "asset" | "layer" | "layer-doc" | "patch" | "properties" | "mask";

function emptyFields(): AssetFieldValue[] {
  return ASSET_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null }));
}

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
}) {
  return (
    <button type="button" className={styles.field} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayAssetValue(value, loading)}</span>
    </button>
  );
}

export function AssetVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(true);
  const [fields, setFields] = useState<AssetFieldValue[]>(emptyFields);
  const [dialog, setDialog] = useState<NameDialogKind | null>(null);
  const [dialogName, setDialogName] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [correctionDraft, setCorrectionDraft] = useState("");
  const fieldsRef = useRef(fields);
  fieldsRef.current = fields;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    fetchAssetReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        if (model.fields.length) {
          setFields((prev) => {
            const map = new Map(prev.map((row) => [row.controlUid, row.value]));
            for (const row of model.fields) {
              if (row.value != null && row.value !== "") map.set(row.controlUid, row.value);
            }
            return ASSET_VISIBLE_CONTROLS.map((controlUid) => ({
              controlUid,
              value: map.get(controlUid) ?? null,
            }));
          });
        }
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof AssetClientError ? cause.code : "ASSET_READ_UNAVAILABLE");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const applyPatch = useCallback((patch: Record<string, string>) => {
    setFields((prev) => {
      const map = new Map(prev.map((row) => [row.controlUid, row.value]));
      for (const [uid, value] of Object.entries(patch)) map.set(uid, value);
      return ASSET_VISIBLE_CONTROLS.map((controlUid) => ({
        controlUid,
        value: map.has(controlUid) ? (map.get(controlUid) ?? null) : null,
      }));
    });
  }, []);

  const act = useCallback(async (controlUid: string, nextValue?: string) => {
    const actionUid = ASSET_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    const patch = previewAssetAction(
      controlUid,
      actionUid,
      (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
      nextValue,
    );
    applyPatch(patch);
    try {
      await postAssetAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue);
    } catch {
      // Optimistic projection stays visible when the write path is unbound.
    }
  }, [applyPatch]);

  const openNameDialog = useCallback((kind: NameDialogKind, preset = "") => {
    setDialogName(preset);
    setDialog(kind);
  }, []);

  const confirmNameDialog = useCallback(() => {
    if (!dialog) return;
    const name = dialogName.trim();
    if (dialog === "project") void act("ASSET-01-CTL-PROJECT", name || undefined);
    if (dialog === "topic") void act("ASSET-01-CTL-TOPIC", name || undefined);
    if (dialog === "asset") void act("ASSET-01-LST-ASSET", name || undefined);
    if (dialog === "layer") void act("ASSET-01-BTN-LAYER-ADD", name || undefined);
    if (dialog === "layer-doc") void act("ASSET-01-BTN-LAYER-DOC-CREATE", name || undefined);
    if (dialog === "patch") void act("ASSET-01-BTN-PATCH-CREATE", name || undefined);
    if (dialog === "properties") void act("ASSET-01-CTL-LAYER-PROPERTIES", name || undefined);
    if (dialog === "mask") void act("ASSET-01-CTL-LAYER-MASK", name || undefined);
    setDialog(null);
    setDialogName("");
  }, [act, dialog, dialogName]);

  const submitSearch = useCallback(() => {
    const query = searchDraft.trim();
    void act("ASSET-01-FLD-SEARCH", query || undefined);
  }, [act, searchDraft]);

  const submitCorrection = useCallback(() => {
    const text = correctionDraft.trim();
    void act("ASSET-01-BTN-CORRECTION-OPEN", text || undefined);
  }, [act, correctionDraft]);

  const disabled = false;
  const tx = (key: TranslationKey) => t(key);
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const modeValue = valueOf("ASSET-01-CTL-MODE");
  const modeLabel = modeValue === "MANUAL" ? tx("asset.mode_manual") : modeValue === "AUTO" ? tx("asset.mode_auto") : tx("asset.mode");
  const filterValue = valueOf("ASSET-01-CTL-FILTER");
  const filterLabel =
    filterValue === "REQUIRED"
      ? tx("asset.required")
      : filterValue === "REUSE"
        ? tx("asset.reuse")
        : filterValue === "MISSING"
          ? tx("asset.missing")
          : filterValue === "DEFERRED"
            ? tx("asset.deferred")
            : tx("asset.filter_all");
  const assets = usableList(valueOf("ASSET-01-LST-ASSET"));
  const selectedAsset = valueOf("ASSET-01-FLD-MANIFEST");
  const compareMode = valueOf("ASSET-01-LST-COMPARE-VERSIONS");
  const previewLabel = selectedAsset && selectedAsset !== "created" ? selectedAsset : tx("asset.preview_unbound");
  const layers = usableList(valueOf("ASSET-01-BTN-LAYER-ADD"));
  const dialogTitleKey: TranslationKey =
    dialog === "topic"
      ? "asset.dialog_rename_topic"
      : dialog === "asset"
        ? "asset.dialog_asset"
        : dialog === "layer"
          ? "asset.dialog_layer"
          : dialog === "layer-doc"
            ? "asset.dialog_layer_doc"
            : dialog === "patch"
              ? "asset.dialog_patch"
              : dialog === "properties"
                ? "asset.dialog_properties"
                : dialog === "mask"
                  ? "asset.dialog_mask"
                  : "asset.dialog_rename_project";
  const dialogDefault =
    dialog === "topic"
      ? tx("asset.default_topic")
      : dialog === "asset"
        ? tx("asset.default_asset")
        : dialog === "layer"
          ? tx("asset.default_layer")
          : dialog === "layer-doc"
            ? tx("asset.dialog_layer_doc")
            : dialog === "patch"
              ? tx("asset.dialog_patch")
              : dialog === "properties"
                ? tx("asset.layer_properties")
                : dialog === "mask"
                  ? tx("asset.layer_mask")
                  : tx("asset.default_project");
  const zoomLabel = displayAssetValue(valueOf("ASSET-01-BTN-FIT"), loading);

  return (
    <div
      className={styles.page}
      data-page-uid="ASSET-01"
      data-page-state={pageState}
      data-component-count="16"
      data-control-count="85"
      aria-label={tx("asset.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("asset.error")}</div> : null}

      <section className={styles.context} data-component-uid="ASSET-01-CMP-CONTEXT">
        <Field uid="ASSET-01-CTL-PROJECT" label={tx("asset.project")} value={valueOf("ASSET-01-CTL-PROJECT")} loading={loading} onAct={() => openNameDialog("project", valueOf("ASSET-01-CTL-PROJECT") ?? "")} disabled={disabled} />
        <Field uid="ASSET-01-CTL-TOPIC" label={tx("asset.topic")} value={valueOf("ASSET-01-CTL-TOPIC")} loading={loading} onAct={() => openNameDialog("topic", valueOf("ASSET-01-CTL-TOPIC") ?? "")} disabled={disabled} />
        <Field uid="ASSET-01-FLD-TASK" label={tx("asset.task")} value={valueOf("ASSET-01-FLD-TASK")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="ASSET-01-FLD-TASK-STATUS" label={tx("asset.task_status")} value={valueOf("ASSET-01-FLD-TASK-STATUS")} loading={loading} onAct={act} disabled={disabled} />
        <button type="button" className={styles.btn} data-control-uid="ASSET-01-CTL-MODE" disabled={disabled} onClick={() => void act("ASSET-01-CTL-MODE")}>
          {tx("asset.mode")} {modeLabel === tx("asset.mode") ? displayAssetValue(modeValue, loading) : modeLabel}
        </button>
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="ASSET-01-BTN-EXECUTE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-EXECUTE")}>{tx("asset.execute")}</button>
        <Field uid="ASSET-01-FLD-STAGE" label={tx("asset.stage")} value={valueOf("ASSET-01-FLD-STAGE")} loading={loading} onAct={act} disabled={disabled} />
      </section>

      <div className={styles.body}>
        <aside className={styles.left}>
          <section data-component-uid="ASSET-01-CMP-ASSET-LIST">
            <h2 className={styles.title}>{tx("asset.manifest_list")}</h2>
            <label className={styles.search}>
              <span className={styles.label}>{tx("asset.search")}</span>
              <input
                data-control-uid="ASSET-01-FLD-SEARCH"
                disabled={disabled}
                placeholder={tx("asset.search")}
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                onBlur={submitSearch}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    submitSearch();
                  }
                }}
              />
            </label>
            <div className={styles.filter}>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-CTL-FILTER" disabled={disabled} onClick={() => void act("ASSET-01-CTL-FILTER")}>
                {tx("asset.filter")} {filterLabel}
              </button>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="ASSET-01-LST-ASSET" disabled={disabled} onClick={() => openNameDialog("asset")}>
                {tx("asset.add_asset")}
              </button>
            </div>
            <div className={styles.list} data-control-uid="ASSET-01-LST-ASSET">
              {assets.length ? (
                assets.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={`${styles.item} ${item === selectedAsset ? styles.itemActive : ""}`}
                    disabled={disabled}
                    onClick={() => void act("ASSET-01-LST-ASSET", item)}
                  >
                    <span>{item}</span>
                    <span>{item === selectedAsset ? displayAssetValue("selected", false) : ""}</span>
                  </button>
                ))
              ) : (
                <button type="button" className={styles.item} disabled={disabled} onClick={() => openNameDialog("asset")}>
                  <span>{tx("asset.unbound_item")}</span>
                  <span>{displayAssetValue(null, loading)}</span>
                </button>
              )}
            </div>
            {valueOf("ASSET-01-FLD-SEARCH") ? (
              <p className={styles.note}>{tx("asset.search")}：{valueOf("ASSET-01-FLD-SEARCH")}</p>
            ) : null}
          </section>
          <section data-component-uid="ASSET-01-CMP-REUSE">
            <h3 className={styles.sub}>{tx("asset.reuse_first")}</h3>
            <div className={styles.reuse}>
              {ASSET_REUSE_FIELDS.map(([uid, key]) => (
                <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
              ))}
            </div>
          </section>
        </aside>

        <main className={styles.center}>
          <section data-component-uid="ASSET-01-CMP-COMPARE">
            <h2 className={styles.title}>{tx("asset.preview_compare")}</h2>
            <div className={styles.toolbar}>
              <button type="button" className={`${styles.btn} ${valueOf("ASSET-01-BTN-SINGLE") === "active" || !compareMode || compareMode === "單張" ? styles.active : ""}`} data-control-uid="ASSET-01-BTN-SINGLE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-SINGLE")}>{tx("asset.single")}</button>
              <button type="button" className={`${styles.btn} ${valueOf("ASSET-01-BTN-AB") === "active" ? styles.active : ""}`} data-control-uid="ASSET-01-BTN-AB" disabled={disabled} onClick={() => void act("ASSET-01-BTN-AB")}>{tx("asset.ab")}</button>
              <button type="button" className={`${styles.btn} ${valueOf("ASSET-01-BTN-ABC") === "active" ? styles.active : ""}`} data-control-uid="ASSET-01-BTN-ABC" disabled={disabled} onClick={() => void act("ASSET-01-BTN-ABC")}>{tx("asset.abc")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-ZOOM-OUT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-ZOOM-OUT")}>{tx("asset.zoom_out")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-ZOOM-IN" disabled={disabled} onClick={() => void act("ASSET-01-BTN-ZOOM-IN")}>{tx("asset.zoom_in")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-FIT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-FIT")}>{tx("asset.fit")} {zoomLabel === "—" ? "" : zoomLabel}</button>
              <button type="button" className={`${styles.btn} ${valueOf("ASSET-01-BTN-REFERENCE") === "attached" ? styles.active : ""}`} data-control-uid="ASSET-01-BTN-REFERENCE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-REFERENCE")}>{tx("asset.reference")}</button>
            </div>
          </section>
          <section data-component-uid="ASSET-01-CMP-PREVIEW">
            <div className={styles.preview}>{previewLabel}</div>
            <div className={styles.list} data-control-uid="ASSET-01-LST-COMPARE-VERSIONS">
              <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("ASSET-01-LST-COMPARE-VERSIONS")}>
                <span>{tx("asset.selected_versions")}</span>
                <span>{displayAssetValue(compareMode, loading)}</span>
              </button>
            </div>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-RESULT-DETAIL" disabled={disabled} onClick={() => void act("ASSET-01-BTN-RESULT-DETAIL")}>{tx("asset.result_detail")}</button>
          </section>
        </main>

        <aside className={styles.right}>
          <section data-component-uid="ASSET-01-CMP-BINDING">
            <h2 className={styles.title}>{tx("asset.binding")}</h2>
            {ASSET_BINDING_FIELDS.map(([uid, key]) => (
              <div key={uid} className={styles.kv}>
                <span>{tx(key)}</span>
                <button type="button" className={styles.btn} data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
                  {displayAssetValue(valueOf(uid), loading)}
                </button>
              </div>
            ))}
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="ASSET-01-BTN-BLUEPRINT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-BLUEPRINT")}>{tx("asset.view_blueprint")}</button>
          </section>
          <section data-component-uid="ASSET-01-CMP-SCRIPT">
            <h3 className={styles.sub}>{tx("asset.script_view")}</h3>
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="ASSET-01-BTN-SCRIPT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-SCRIPT")}>{tx("asset.view_script")}</button>
          </section>
          <section data-component-uid="ASSET-01-CMP-SCORE">
            <h3 className={styles.sub}>{tx("asset.scorecard")}</h3>
            {ASSET_SCORE_FIELDS.map(([uid, key]) => (
              <div key={uid} className={styles.kv}>
                <span>{tx(key)}</span>
                <button type="button" className={styles.btn} data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
                  {displayAssetValue(valueOf(uid), loading)}
                </button>
              </div>
            ))}
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="ASSET-01-BTN-EVALUATE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-EVALUATE")}>{tx("asset.evaluate")}</button>
          </section>
          <section data-component-uid="ASSET-01-CMP-VERSION">
            <h3 className={styles.sub}>{tx("asset.version")}</h3>
            <div className={styles.railActions}>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-VERSION-HISTORY" disabled={disabled} onClick={() => void act("ASSET-01-BTN-VERSION-HISTORY")}>{tx("asset.version_history")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-RESTORE-AS-NEW" disabled={disabled} onClick={() => void act("ASSET-01-BTN-RESTORE-AS-NEW")}>{tx("asset.restore_as_new")}</button>
            </div>
          </section>
          <section data-component-uid="ASSET-01-CMP-DECISION">
            <h3 className={styles.sub}>{tx("asset.decision")}</h3>
            <div className={styles.decisionRow}>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="ASSET-01-BTN-CONFIRM" disabled={disabled} onClick={() => void act("ASSET-01-BTN-CONFIRM")}>{tx("asset.confirm")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-MODIFY" disabled={disabled} onClick={submitCorrection}>{tx("asset.modify")}</button>
              <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LOCK" disabled={disabled} onClick={() => void act("ASSET-01-BTN-LOCK")}>{tx("asset.lock")}</button>
            </div>
          </section>
        </aside>
      </div>

      <div className={styles.lower}>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-CORRECTION">
          <h3 className={styles.sub}>{tx("asset.correction")}</h3>
          <div className={styles.toolbar}>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-CORRECTION-OPEN" disabled={disabled} onClick={submitCorrection}>{tx("asset.correction_open")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-CORRECTION-GENERATE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-CORRECTION-GENERATE", correctionDraft.trim() || undefined)}>{tx("asset.correction_generate")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-CORRECTION-APPROVE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-CORRECTION-APPROVE")}>{tx("asset.correction_approve")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-CORRECTION-EXECUTE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-CORRECTION-EXECUTE")}>{tx("asset.correction_execute")}</button>
          </div>
          <label className={styles.composerInput}>
            <span className={styles.label}>{tx("asset.correction_request")}</span>
            <textarea
              data-control-uid="ASSET-01-TXT-CORRECTION-REQUEST"
              disabled={disabled}
              value={correctionDraft}
              onChange={(event) => setCorrectionDraft(event.target.value)}
              onBlur={() => {
                if (correctionDraft.trim()) void act("ASSET-01-TXT-CORRECTION-REQUEST", correctionDraft.trim());
              }}
            />
          </label>
        </section>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-LAYER-STACK">
          <h3 className={styles.sub}>{tx("asset.layer_stack")}</h3>
          <div className={styles.layerActions}>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-DOC-CREATE" disabled={disabled} onClick={() => openNameDialog("layer-doc")}>{tx("asset.layer_doc_create")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-DOC-UPDATE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-LAYER-DOC-UPDATE")}>{tx("asset.layer_doc_update")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-ADD" disabled={disabled} onClick={() => openNameDialog("layer")}>{tx("asset.layer_add")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-DELETE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-LAYER-DELETE")}>{tx("asset.layer_delete")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-DUPLICATE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-LAYER-DUPLICATE")}>{tx("asset.layer_duplicate")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-LAYER-REORDER" disabled={disabled} onClick={() => void act("ASSET-01-BTN-LAYER-REORDER")}>{tx("asset.layer_reorder")}</button>
          </div>
          <div className={styles.list}>
            {layers.map((layer) => (
              <div key={layer} className={styles.item}>
                <span>{layer}</span>
              </div>
            ))}
          </div>
          <p className={styles.note}>{tx("asset.layer_na")}</p>
        </section>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-LAYER-INSPECTOR">
          <h3 className={styles.sub}>{tx("asset.layer_inspector")}</h3>
          <Field uid="ASSET-01-CTL-LAYER-PROPERTIES" label={tx("asset.layer_properties")} value={valueOf("ASSET-01-CTL-LAYER-PROPERTIES")} loading={loading} onAct={() => openNameDialog("properties", valueOf("ASSET-01-CTL-LAYER-PROPERTIES") ?? "")} disabled={disabled} />
          <Field uid="ASSET-01-CTL-LAYER-MASK" label={tx("asset.layer_mask")} value={valueOf("ASSET-01-CTL-LAYER-MASK")} loading={loading} onAct={() => openNameDialog("mask", valueOf("ASSET-01-CTL-LAYER-MASK") ?? "")} disabled={disabled} />
        </section>
      </div>

      <div className={styles.lower}>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-PATCH">
          <h3 className={styles.sub}>{tx("asset.patch")}</h3>
          <div className={styles.patchActions}>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-PATCH-CREATE" disabled={disabled} onClick={() => openNameDialog("patch")}>{tx("asset.patch_create")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-PATCH-PREVIEW" disabled={disabled} onClick={() => void act("ASSET-01-BTN-PATCH-PREVIEW")}>{tx("asset.patch_preview")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-PATCH-ACCEPT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-PATCH-ACCEPT")}>{tx("asset.patch_accept")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-PATCH-REJECT" disabled={disabled} onClick={() => void act("ASSET-01-BTN-PATCH-REJECT")}>{tx("asset.patch_reject")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-PATCH-REVISE" disabled={disabled} onClick={() => void act("ASSET-01-BTN-PATCH-REVISE")}>{tx("asset.patch_revise")}</button>
          </div>
        </section>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-RUNTIME">
          <h3 className={styles.sub}>{tx("asset.runtime")}</h3>
          {ASSET_RUNTIME_FIELDS.map(([uid, key]) => (
            <div key={uid} className={styles.kv}>
              <span>{tx(key)}</span>
              <button type="button" className={styles.btn} data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
                {displayAssetValue(valueOf(uid), loading)}
              </button>
            </div>
          ))}
          <div className={styles.railActions}>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-RETRY" disabled={disabled} onClick={() => void act("ASSET-01-BTN-RETRY")}>{tx("asset.retry")}</button>
            <button type="button" className={styles.btn} data-control-uid="ASSET-01-BTN-RUNTIME-DETAIL" disabled={disabled} onClick={() => void act("ASSET-01-BTN-RUNTIME-DETAIL")}>{tx("asset.runtime_detail")}</button>
          </div>
        </section>
        <section className={styles.block} data-component-uid="ASSET-01-CMP-HANDOFF">
          <h3 className={styles.sub}>{tx("asset.handoff")}</h3>
          <div className={styles.handoff}>
            {ASSET_HANDOFF_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
            ))}
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="ASSET-01-BTN-HANDOFF" disabled={disabled} onClick={() => void act("ASSET-01-BTN-HANDOFF")}>{tx("asset.handoff_video")}</button>
          </div>
        </section>
      </div>
      {dialog ? (
        <div className={styles.dialogScrim} role="presentation" onClick={() => setDialog(null)}>
          <form
            className={styles.dialog}
            onClick={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              confirmNameDialog();
            }}
          >
            <h2>{tx(dialogTitleKey)}</h2>
            <label>
              <span className={styles.label}>{tx("asset.name_placeholder")}</span>
              <input
                autoFocus
                value={dialogName}
                placeholder={dialogDefault}
                onChange={(event) => setDialogName(event.target.value)}
              />
            </label>
            <div className={styles.dialogActions}>
              <button type="button" className={styles.btn} onClick={() => setDialog(null)}>{tx("asset.dialog_cancel")}</button>
              <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>{tx("asset.dialog_confirm")}</button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
