"use client";

import { useI18n } from "@/i18n/LocaleProvider";
import { iamText } from "@/i18n/iamCatalog";
import {
  getIamControlRuntime,
  getIamPageState,
  IamGovernedButton,
  IamRuntimeProvider,
  invokeIamControl,
  isIamEffectfulRuntimeReady,
  isIamProjectionRuntimeReady,
  selectIamAccount,
  setIamAdminL1,
  setIamBasicField,
  setIamDepartmentPreset,
  setIamFrontL1,
  setIamSearchQuery,
  useIamRuntimeState,
} from "./IamControlRuntime";
import { IAM_CONTROL_BINDING_COUNT } from "@/domain/iam/iamControlBindings";
import styles from "./IamVisual.module.css";

const FRONT_L1 = [
  ["FRONT-L1-01", "儀表板", "仪表板", "Dashboard"],
  ["FRONT-L1-02", "專案 / 專題", "项目 / 专题", "Project / Topic"],
  ["FRONT-L1-03", "素材", "素材", "Assets"],
  ["FRONT-L1-04", "影片", "影片", "Video"],
  ["FRONT-L1-05", "剪輯配音", "剪辑配音", "Editing & Voice"],
  ["FRONT-L1-06", "QA", "QA", "QA"],
  ["FRONT-L1-07", "資料庫", "数据库", "Database"],
  ["FRONT-L1-08", "戰略中心", "战略中心", "Strategy Center"],
  ["FRONT-L1-09", "最新資訊", "最新资讯", "Latest Information"],
] as const;

const ADMIN_L1 = [
  ["ADMIN-L1-SYSTEM", "系統維護", "系统维护", "System Maintenance"],
  ["ADMIN-L1-IAM", "帳戶與權限", "账户与权限", "Accounts & Permissions"],
  ["ADMIN-L1-DEV", "企業自動開發系統", "企业自动开发系统", "Enterprise Automation"],
  ["ADMIN-L1-SOCIAL", "社群發布", "社群发布", "Social Publishing"],
  ["ADMIN-L1-ERP", "ERP", "ERP", "ERP"],
  ["ADMIN-L1-AIAPI", "AI API", "AI API", "AI API"],
  ["ADMIN-L1-QA-CRITERIA", "QA 評分項目", "QA 评分项目", "QA Review Criteria"],
  ["ADMIN-L1-STRATEGY", "戰略中心", "战略中心", "Strategy Administration"],
  ["ADMIN-L1-KNOWLEDGE", "知識庫", "知识库", "Knowledge & Experience"],
] as const;

function label(locale: string, item: readonly [string, string, string, string]) {
  if (locale === "zh-CN") return item[2];
  if (locale === "en") return item[3];
  return item[1];
}

function IamVisualBody() {
  const { locale } = useI18n();
  const runtime = useIamRuntimeState();
  const { client, projection, runtimeError, runtimeErrorUid, runtimeReasonCode, correlationId } = runtime;
  const pageState = getIamPageState(runtime);
  const projectionRuntimeReady = isIamProjectionRuntimeReady();
  const effectfulRuntimeReady = isIamEffectfulRuntimeReady();
  const t = (key: Parameters<typeof iamText>[1]) => iamText(locale, key);
  const selectedAccount = projection?.accounts.find((item) => item.account_id === client.account_id) ?? null;
  const schemaReady = Boolean(projection?.identity_schema.length);
  const presetReady = Boolean(projection?.department_presets.length);
  const preview = projection?.preview ?? null;

  const searchControl = getIamControlRuntime(runtime, "IAM-01-CTL-SEARCH");
  const basicControl = getIamControlRuntime(runtime, "IAM-01-CTL-BASIC-DATA");
  const presetControl = getIamControlRuntime(runtime, "IAM-01-SEL-DEPT-PRESET");
  const frontAllControl = getIamControlRuntime(runtime, "IAM-01-CHK-FRONT-ALL");
  const frontGroupControl = getIamControlRuntime(runtime, "IAM-01-GRP-FRONT-L1");
  const backAllControl = getIamControlRuntime(runtime, "IAM-01-CHK-BACK-ALL");
  const backGroupControl = getIamControlRuntime(runtime, "IAM-01-GRP-BACK-L1");
  const basicActive = pageState.endsWith("_BASIC");
  const permissionActive = pageState.endsWith("_PERMISSION");
  const previewActive = pageState.endsWith("_PREVIEW") || pageState === "APPLYING" || pageState === "COMPLETE";

  return (
    <div
      className={styles.page}
      data-page-uid="admin:IAM-01"
      data-vis-step="VIS-11"
      data-page-state={pageState}
      data-authority-status="FINAL_LOCKED"
      data-authority-sections="6"
      data-authority-components="10"
      data-authority-controls="14"
      data-frontend-l1-count="9"
      data-backend-l1-count="9"
      data-control-registry-valid={IAM_CONTROL_BINDING_COUNT === 14 ? "true" : "false"}
      data-projection-status={runtimeReasonCode ? "BLOCKED" : projection ? "BOUND" : "LOADING"}
      data-projection-reason={runtimeReasonCode ?? undefined}
      data-runtime-error-uid={runtimeErrorUid ?? undefined}
      data-correlation-id={correlationId ?? undefined}
      data-projection-adapter-ready={projectionRuntimeReady ? "true" : "false"}
      data-effectful-runtime-ready={effectfulRuntimeReady ? "true" : "false"}
      data-formal-runtime-status={effectfulRuntimeReady ? "BOUND" : "NOT_EXECUTED"}
    >
      <section className={styles.contextBar} data-section-id="IAM-01-SEC-01" data-component-id="IAM-01-CMP-CONTEXT">
        <div>
          <div className={styles.eyebrow}>IAM-01 · ACCOUNT PERMISSION ASSIGNMENT</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextActions}>
          <div className={styles.countBox}><span>{t("authorizedCount")}</span><strong>{projection?.authorized_account_count ?? "—"}</strong></div>
          <IamGovernedButton className={styles.primaryButton} controlId="IAM-01-BTN-ADD">{t("addAccount")}</IamGovernedButton>
        </div>
      </section>

      <div className={styles.primaryGrid}>
        <div className={styles.leftStack}>
          <section className={styles.panel} data-section-id="IAM-01-SEC-02" data-component-id="IAM-01-CMP-ACCOUNT-LIST">
            <div className={styles.panelHeader}><h2>{t("directory")}</h2><span>READ PROJECTION</span></div>
            <label className={styles.control}>
              <span>{t("search")}</span>
              <input
                data-control-id="IAM-01-CTL-SEARCH"
                data-action-uid={searchControl.binding?.action_uid}
                data-gate-uid={searchControl.binding?.gate_uid}
                data-permission-uid={searchControl.binding?.permission}
                data-effect-type={searchControl.binding?.effect_type}
                data-operation={searchControl.binding?.operation ?? undefined}
                data-method-path={searchControl.binding?.method_path ?? undefined}
                data-current-state={pageState}
                data-runtime-binding={searchControl.runtimeBinding}
                data-gate-allowed={searchControl.gateAllowed ? "true" : "false"}
                data-disabled-reason={searchControl.disabledReason ?? undefined}
                data-search-trigger="ENTER"
                value={client.search_query}
                onChange={(event) => setIamSearchQuery(runtime, event.currentTarget.value)}
                onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void invokeIamControl(runtime, "IAM-01-CTL-SEARCH"); } }}
                disabled={!searchControl.enabled}
                placeholder={t("searchHint")}
              />
            </label>
            {projection?.accounts.length ? (
              <div className={styles.accountList}>
                {projection.accounts.map((account) => (
                  <button
                    key={account.account_id}
                    type="button"
                    className={`${styles.accountRow} ${client.account_id === account.account_id ? styles.accountRowActive : ""}`}
                    data-account-id={account.account_id}
                    disabled={!searchControl.gateAllowed}
                    onClick={() => selectIamAccount(runtime, account.account_id)}
                  >
                    <span><strong>{account.label}</strong><small>{account.account_id}</small></span>
                    <code>{account.status}</code>
                  </button>
                ))}
              </div>
            ) : (
              <div className={styles.directoryEmpty}><div className={styles.emptyIcon}>◎</div><strong>{t("noAccounts")}</strong><span>IdentityService / IAM projection</span></div>
            )}
          </section>

          <section className={styles.panel} data-section-id="IAM-01-SEC-03" data-component-id="IAM-01-CMP-ACCOUNT-DETAIL">
            <div className={styles.panelHeader}><h2>{t("accountDetail")}</h2><IamGovernedButton className={styles.compactButton} controlId="IAM-01-BTN-EDIT" selectedAccountId={selectedAccount?.account_id}>{t("edit")}</IamGovernedButton></div>
            <div className={styles.detailGrid}>
              {[
                [t("identitySource"), selectedAccount?.identity_source ?? "—"],
                [t("membership"), selectedAccount?.organization_scope ?? "—"],
                [t("mfa"), selectedAccount?.mfa ?? "—"],
                [t("risk"), selectedAccount?.risk ?? "—"],
                [t("session"), selectedAccount?.session ?? "—"],
                [t("effective"), selectedAccount ? `${selectedAccount.front_l1.length + selectedAccount.admin_l1.length} L1` : "—"],
              ].map(([name, value]) => <div className={styles.detailCell} key={name}><span>{name}</span><strong>{value}</strong></div>)}
            </div>
          </section>
        </div>

        <section className={`${styles.panel} ${styles.flowPanel}`} data-section-id="IAM-01-SEC-04">
          <div className={styles.panelHeader}><h2>{t("flow")}</h2><span>{runtimeReasonCode ? "BLOCKED" : client.mode ?? pageState}</span></div>
          <div className={styles.stepper} data-component-id="IAM-01-CMP-STEPPER">
            <div className={`${styles.step} ${basicActive ? styles.stepActive : ""}`}>{t("step1")}</div>
            <div className={`${styles.step} ${permissionActive ? styles.stepActive : ""}`}>{t("step2")}</div>
            <div className={`${styles.step} ${previewActive ? styles.stepActive : ""}`}>{t("step3")}</div>
          </div>

          {schemaReady ? (
            <div
              className={styles.schemaForm}
              data-component-id="IAM-01-CMP-BASIC-DATA"
              data-control-id="IAM-01-CTL-BASIC-DATA"
              data-action-uid={basicControl.binding?.action_uid}
              data-gate-uid={basicControl.binding?.gate_uid}
              data-permission-uid={basicControl.binding?.permission}
              data-effect-type={basicControl.binding?.effect_type}
              data-current-state={pageState}
              data-runtime-binding={basicControl.runtimeBinding}
              data-gate-allowed={basicControl.gateAllowed ? "true" : "false"}
              data-disabled-reason={basicControl.disabledReason ?? undefined}
              data-schema-status="BOUND"
              aria-disabled={!basicControl.enabled}
            >
              <div className={styles.schemaNote}>{t("schemaReady")}</div>
              {projection?.identity_schema.map((field) => (
                <label key={field.field_uid} className={styles.control}>
                  <span>{field.label}</span>
                  <input
                    data-field-uid={field.field_uid}
                    value={client.basic_data[field.field_uid] ?? ""}
                    required={field.required}
                    disabled={!basicControl.enabled}
                    onChange={(event) => setIamBasicField(runtime, field.field_uid, event.currentTarget.value)}
                  />
                </label>
              ))}
            </div>
          ) : (
            <div
              className={styles.blockedForm}
              data-component-id="IAM-01-CMP-BASIC-DATA"
              data-control-id="IAM-01-CTL-BASIC-DATA"
              data-action-uid={basicControl.binding?.action_uid}
              data-gate-uid={basicControl.binding?.gate_uid}
              data-permission-uid={basicControl.binding?.permission}
              data-effect-type={basicControl.binding?.effect_type}
              data-current-state={pageState}
              data-runtime-binding="NOT_EXECUTED"
              data-disabled-reason="IAM-01-ERR-IDENTITY-SCHEMA"
              data-schema-status="BLOCKED"
              aria-disabled="true"
            >
              <div className={styles.blockedTitle}>BLOCK · IDENTITY SCHEMA</div><p>{t("schemaBlocked")}</p>
            </div>
          )}

          <label className={styles.control} data-component-id="IAM-01-CMP-PERMISSION-PRESET">
            <span>{t("preset")}</span>
            <select
              data-control-id="IAM-01-SEL-DEPT-PRESET"
              data-action-uid={presetControl.binding?.action_uid}
              data-gate-uid={presetControl.binding?.gate_uid}
              data-permission-uid={presetControl.binding?.permission}
              data-effect-type={presetControl.binding?.effect_type}
              data-current-state={pageState}
              data-runtime-binding={presetControl.runtimeBinding}
              data-gate-allowed={presetControl.gateAllowed ? "true" : "false"}
              data-disabled-reason={presetReady ? presetControl.disabledReason ?? undefined : "IAM-01-ERR-PRESET"}
              value={client.department_preset_ref ?? ""}
              disabled={!presetControl.enabled || !presetReady}
              onChange={(event) => setIamDepartmentPreset(runtime, event.currentTarget.value || null)}
            >
              <option value="">{t("noPreset")}</option>
              {projection?.department_presets.map((preset) => <option key={preset.ref} value={preset.ref}>{preset.label}</option>)}
            </select>
          </label>

          <div className={styles.permissionColumns}>
            <div className={styles.permissionGroup} data-component-id="IAM-01-CMP-FRONT-L1">
              <label className={styles.groupHeader}>
                <input type="checkbox" data-control-id="IAM-01-CHK-FRONT-ALL" data-action-uid={frontAllControl.binding?.action_uid} data-gate-uid={frontAllControl.binding?.gate_uid} data-permission-uid={frontAllControl.binding?.permission} data-effect-type={frontAllControl.binding?.effect_type} data-current-state={pageState} data-runtime-binding={frontAllControl.runtimeBinding} data-gate-allowed={frontAllControl.gateAllowed ? "true" : "false"} data-disabled-reason={frontAllControl.disabledReason ?? undefined} checked={client.front_l1.length === 9} disabled={!frontAllControl.enabled} onChange={() => runtime.setClient(client.front_l1.length === 9 ? { ...client, front_l1: [] } : { ...client, front_l1: FRONT_L1.map((item) => item[0]) })} />
                <span>{t("frontAll")}</span>
              </label>
              <div className={styles.groupBody} data-control-id="IAM-01-GRP-FRONT-L1" data-action-uid={frontGroupControl.binding?.action_uid} data-gate-uid={frontGroupControl.binding?.gate_uid} data-permission-uid={frontGroupControl.binding?.permission} data-effect-type={frontGroupControl.binding?.effect_type} data-current-state={pageState} data-runtime-binding={frontGroupControl.runtimeBinding} data-gate-allowed={frontGroupControl.gateAllowed ? "true" : "false"} data-disabled-reason={frontGroupControl.disabledReason ?? undefined} aria-disabled={!frontGroupControl.enabled}>
                <div className={styles.groupTitle}>{t("frontL1")}</div>
                {FRONT_L1.map((item) => <label key={item[0]} className={styles.permissionRow}><input type="checkbox" checked={client.front_l1.includes(item[0])} disabled={!frontGroupControl.enabled} onChange={(event) => setIamFrontL1(runtime, item[0], event.currentTarget.checked)} /><span>{label(locale, item)}</span><code>{item[0]}</code></label>)}
              </div>
            </div>
            <div className={styles.permissionGroup} data-component-id="IAM-01-CMP-BACK-L1">
              <label className={styles.groupHeader}>
                <input type="checkbox" data-control-id="IAM-01-CHK-BACK-ALL" data-action-uid={backAllControl.binding?.action_uid} data-gate-uid={backAllControl.binding?.gate_uid} data-permission-uid={backAllControl.binding?.permission} data-effect-type={backAllControl.binding?.effect_type} data-current-state={pageState} data-runtime-binding={backAllControl.runtimeBinding} data-gate-allowed={backAllControl.gateAllowed ? "true" : "false"} data-disabled-reason={backAllControl.disabledReason ?? undefined} checked={client.admin_l1.length === 9} disabled={!backAllControl.enabled} onChange={() => runtime.setClient(client.admin_l1.length === 9 ? { ...client, admin_l1: [] } : { ...client, admin_l1: ADMIN_L1.map((item) => item[0]) })} />
                <span>{t("backAll")}</span>
              </label>
              <div className={styles.groupBody} data-control-id="IAM-01-GRP-BACK-L1" data-action-uid={backGroupControl.binding?.action_uid} data-gate-uid={backGroupControl.binding?.gate_uid} data-permission-uid={backGroupControl.binding?.permission} data-effect-type={backGroupControl.binding?.effect_type} data-current-state={pageState} data-runtime-binding={backGroupControl.runtimeBinding} data-gate-allowed={backGroupControl.gateAllowed ? "true" : "false"} data-disabled-reason={backGroupControl.disabledReason ?? undefined} aria-disabled={!backGroupControl.enabled}>
                <div className={styles.groupTitle}>{t("backL1")}</div>
                {ADMIN_L1.map((item) => <label key={item[0]} className={styles.permissionRow}><input type="checkbox" checked={client.admin_l1.includes(item[0])} disabled={!backGroupControl.enabled} onChange={(event) => setIamAdminL1(runtime, item[0], event.currentTarget.checked)} /><span>{label(locale, item)}</span><code>{item[0]}</code></label>)}
              </div>
            </div>
          </div>

          <div className={styles.actionRow}>
            <IamGovernedButton controlId="IAM-01-BTN-SAVE-DRAFT">{t("saveDraft")}</IamGovernedButton>
            <IamGovernedButton controlId="IAM-01-BTN-VALIDATE">{t("validate")}</IamGovernedButton>
            <IamGovernedButton controlId="IAM-01-BTN-PREVIEW">{t("previewButton")}</IamGovernedButton>
            <IamGovernedButton className={styles.primaryButton} controlId="IAM-01-BTN-COMPLETE" confirmationMessage={t("completeConfirm")}>{t("complete")}</IamGovernedButton>
          </div>
          <div className={styles.phaseNote}>{runtimeError ?? pageState}</div>
        </section>
      </div>

      <section className={styles.panel} data-section-id="IAM-01-SEC-05" data-component-id="IAM-01-CMP-PREVIEW">
        <div className={styles.panelHeader}><h2>{t("preview")}</h2><span>{preview?.preview_ref ?? "PREVIEW FIRST · NO APPLY"}</span></div>
        <div className={styles.previewGrid}>
          {[
            ["ADDED", preview?.added],
            ["REMOVED", preview?.removed],
            ["UNCHANGED", preview?.unchanged],
            ["BLOCKED", preview?.blocked],
          ].map(([state, items]) => {
            const list = Array.isArray(items) ? items : null;
            return <div className={styles.previewCell} key={state as string}><span>{state as string}</span><strong>{list ? list.length : "—"}</strong><small>{list?.join(" · ") || "—"}</small></div>;
          })}
        </div>
        <p className={styles.previewNote}>{t("previewEmpty")}</p>
      </section>

      <section className={styles.panel} data-section-id="IAM-01-SEC-06" data-component-id="IAM-01-CMP-AUDIT">
        <div className={styles.panelHeader}><h2>{t("audit")}</h2><IamGovernedButton className={styles.compactButton} controlId="IAM-01-BTN-AUDIT">{t("audit")}</IamGovernedButton></div>
        {client.audit_open ? (
          <div className={styles.auditList} data-audit-open="true">{projection?.audit_entries.length ? projection.audit_entries.map((entry) => <div key={entry}>{entry}</div>) : <span>—</span>}</div>
        ) : (
          <div className={styles.auditEmpty}><span>{t("auditEmpty")}</span><code>correlation · version · scope · condition · access review</code></div>
        )}
      </section>
    </div>
  );
}

export function IamVisual() {
  return <IamRuntimeProvider><IamVisualBody /></IamRuntimeProvider>;
}
