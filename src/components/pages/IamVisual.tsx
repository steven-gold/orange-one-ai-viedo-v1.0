"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { iamText } from "@/i18n/iamCatalog";
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

export function IamVisual() {
  const { locale } = useI18n();
  const [createMode, setCreateMode] = useState(false);
  const t = (key: Parameters<typeof iamText>[1]) => iamText(locale, key);

  return (
    <div className={styles.page} data-page-uid="admin:IAM-01" data-vis-step="VIS-11" data-page-state={createMode ? "CREATE_BASIC_BLOCKED" : "LIST_EMPTY"}>
      <section className={styles.contextBar} data-section-id="IAM-01-SEC-01" data-component-id="IAM-01-CMP-CONTEXT">
        <div>
          <div className={styles.eyebrow}>IAM-01 · ACCOUNT PERMISSION ASSIGNMENT</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextActions}>
          <div className={styles.countBox}><span>{t("authorizedCount")}</span><strong>—</strong></div>
          <button className={styles.primaryButton} type="button" data-control-id="IAM-01-BTN-ADD" onClick={() => setCreateMode(true)}>{t("addAccount")}</button>
        </div>
      </section>

      <div className={styles.primaryGrid}>
        <div className={styles.leftStack}>
          <section className={styles.panel} data-section-id="IAM-01-SEC-02" data-component-id="IAM-01-CMP-ACCOUNT-LIST">
            <div className={styles.panelHeader}><h2>{t("directory")}</h2><span>64% · READ PROJECTION</span></div>
            <label className={styles.control}><span>{t("search")}</span><input data-control-id="IAM-01-CTL-SEARCH" disabled placeholder="—" /></label>
            <div className={styles.directoryEmpty}><div className={styles.emptyIcon}>◎</div><strong>{t("noAccounts")}</strong><span>IdentityService / IAM projection</span></div>
          </section>

          <section className={styles.panel} data-section-id="IAM-01-SEC-03" data-component-id="IAM-01-CMP-ACCOUNT-DETAIL">
            <div className={styles.panelHeader}><h2>{t("accountDetail")}</h2><button className={styles.compactButton} data-control-id="IAM-01-BTN-EDIT" disabled>{t("edit")}</button></div>
            <div className={styles.detailGrid}>
              {[t("identitySource"), t("membership"), t("mfa"), t("risk"), t("session"), t("effective")].map((name) => (
                <div className={styles.detailCell} key={name}><span>{name}</span><strong>—</strong></div>
              ))}
            </div>
          </section>
        </div>

        <section className={`${styles.panel} ${styles.flowPanel}`} data-section-id="IAM-01-SEC-04">
          <div className={styles.panelHeader}><h2>{t("flow")}</h2><span>{createMode ? "CREATE · BLOCKED" : "LIST"}</span></div>
          <div className={styles.stepper} data-component-id="IAM-01-CMP-STEPPER">
            <div className={`${styles.step} ${createMode ? styles.stepActive : ""}`}>{t("step1")}</div>
            <div className={styles.step}>{t("step2")}</div>
            <div className={styles.step}>{t("step3")}</div>
          </div>
          <div className={styles.blockedForm} data-component-id="IAM-01-CMP-BASIC-DATA" data-control-id="IAM-01-CTL-BASIC-DATA"><div className={styles.blockedTitle}>BLOCK · IDENTITY SCHEMA</div><p>{t("schemaBlocked")}</p></div>
          <label className={styles.control} data-component-id="IAM-01-CMP-PERMISSION-PRESET"><span>{t("preset")}</span><select data-control-id="IAM-01-SEL-DEPT-PRESET" disabled><option>{t("noPreset")}</option></select></label>

          <div className={styles.permissionColumns}>
            <div className={styles.permissionGroup} data-component-id="IAM-01-CMP-FRONT-L1">
              <label className={styles.groupHeader}><input type="checkbox" data-control-id="IAM-01-CHK-FRONT-ALL" disabled /><span>{t("frontAll")}</span></label>
              <div className={styles.groupBody} data-control-id="IAM-01-GRP-FRONT-L1">
                <div className={styles.groupTitle}>{t("frontL1")}</div>
                {FRONT_L1.map((item) => <label key={item[0]} className={styles.permissionRow}><input type="checkbox" disabled /><span>{label(locale, item)}</span><code>{item[0]}</code></label>)}
              </div>
            </div>
            <div className={styles.permissionGroup} data-component-id="IAM-01-CMP-BACK-L1">
              <label className={styles.groupHeader}><input type="checkbox" data-control-id="IAM-01-CHK-BACK-ALL" disabled /><span>{t("backAll")}</span></label>
              <div className={styles.groupBody} data-control-id="IAM-01-GRP-BACK-L1">
                <div className={styles.groupTitle}>{t("backL1")}</div>
                {ADMIN_L1.map((item) => <label key={item[0]} className={styles.permissionRow}><input type="checkbox" disabled /><span>{label(locale, item)}</span><code>{item[0]}</code></label>)}
              </div>
            </div>
          </div>

          <div className={styles.actionRow}>
            <button data-control-id="IAM-01-BTN-SAVE-DRAFT" disabled>{t("saveDraft")}</button>
            <button data-control-id="IAM-01-BTN-VALIDATE" disabled>{t("validate")}</button>
            <button data-control-id="IAM-01-BTN-PREVIEW" disabled>{t("previewButton")}</button>
            <button className={styles.primaryButton} data-control-id="IAM-01-BTN-COMPLETE" disabled>{t("complete")}</button>
          </div>
          <div className={styles.phaseNote}>{t("visualPhase")}</div>
        </section>
      </div>

      <section className={styles.panel} data-section-id="IAM-01-SEC-05" data-component-id="IAM-01-CMP-PREVIEW">
        <div className={styles.panelHeader}><h2>{t("preview")}</h2><span>PREVIEW FIRST · NO APPLY</span></div>
        <div className={styles.previewGrid}>{["ADDED", "REMOVED", "UNCHANGED", "BLOCKED"].map((state) => <div className={styles.previewCell} key={state}><span>{state}</span><strong>—</strong></div>)}</div>
        <p className={styles.previewNote}>{t("previewEmpty")}</p>
      </section>

      <section className={styles.panel} data-section-id="IAM-01-SEC-06" data-component-id="IAM-01-CMP-AUDIT">
        <div className={styles.panelHeader}><h2>{t("audit")}</h2><button className={styles.compactButton} data-control-id="IAM-01-BTN-AUDIT" disabled>{t("audit")}</button></div>
        <div className={styles.auditEmpty}><span>{t("auditEmpty")}</span><code>correlation · version · scope · condition · access review</code></div>
      </section>
    </div>
  );
}
