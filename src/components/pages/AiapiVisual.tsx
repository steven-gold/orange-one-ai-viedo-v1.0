"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { AiapiClientError, fetchAiapiReadModel, postAiapiAction, type AiapiFieldValue } from "@/lib/client";
import { Icon, type IconName } from "@/components/ui/Icon";
import {
  AIAPI_CAPABILITIES,
  AIAPI_PROFILE_FIELD_GROUPS,
  AIAPI_PROMPT_TEMPLATE_TOKEN,
  AIAPI_REGISTRY_UID,
  parseProfiles,
  profileCapabilities,
  profileIdentity,
  type AiapiProfile,
} from "@/lib/aiapiProfiles";
import { displayAiapiStatus, displayAiapiValue } from "./aiapiFormat";
import {
  AIAPI_CONTROL_ACTIONS,
  AIAPI_PRO_DESC_FIELDS,
  AIAPI_PROFILE_GROUPS,
  AIAPI_TABLE_COLUMNS,
  AIAPI_VIEWS,
  AIAPI_VISIBLE_CONTROLS,
  type AiapiView,
} from "./aiapiControls";
import styles from "./AiapiVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const SET_CREDENTIAL_UID = "CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-SET-CREDENTIAL";

const PROFILE_TARGETED_ACTIONS = new Set([
  "updateProviderModelProfile",
  "retireProviderModelProfile",
  "testProviderModelProfile",
  "setProviderModelCredential",
  "deleteProviderModelCredential",
]);

const PROFILE_FIELD_LABELS: Record<string, TranslationKey> = {
  providerId: "aiapi.fld-provider-id",
  providerName: "aiapi.fld-provider-name",
  modelId: "aiapi.fld-model-id",
  modelName: "aiapi.fld-model-name",
  baseUrl: "aiapi.fld-base-url",
  endpointPath: "aiapi.fld-endpoint-path",
  httpMethod: "aiapi.fld-http-method",
  timeoutSeconds: "aiapi.fld-timeout",
  adapterType: "aiapi.fld-adapter-type",
  requestTemplate: "aiapi.fld-request-template",
  responseTextPath: "aiapi.fld-response-path",
  promptTemplate: "aiapi.fld-prompt-template",
  capabilityType: "aiapi.fld-capability-type",
  additionalCapabilities: "aiapi.fld-additional-capabilities",
  supportsReferences: "aiapi.fld-supports-references",
  rightsCompatible: "aiapi.fld-rights-compatible",
  dataClassifications: "aiapi.fld-data-classifications",
  preferredLanguage: "aiapi.fld-preferred-language",
  maxContext: "aiapi.fld-max-context",
  enabled: "aiapi.fld-enabled",
};

const REQUIRED_PROFILE_FIELDS = new Set([
  "providerId",
  "modelId",
  "capabilityType",
  "adapterType",
  "baseUrl",
  "endpointPath",
  "promptTemplate",
]);

type FormField = {
  key: string;
  labelKey: TranslationKey;
  required?: boolean;
  kind?: "text" | "capability" | "enabled" | "yesno" | "secret" | "method";
};

const CREDENTIAL_FIELD: FormField = {
  key: "secret",
  labelKey: "aiapi.form-credential-secret",
  required: true,
  kind: "secret",
};

const MODAL_FORMS: Record<string, FormField[]> = {
  setProviderModelCredential: [CREDENTIAL_FIELD],
  configureGovernedResource: [
    { key: "reference", labelKey: "aiapi.form-governed-ref", required: true },
    { key: "capability", labelKey: "aiapi.form-capability" },
    { key: "rights", labelKey: "aiapi.form-rights" },
    { key: "data", labelKey: "aiapi.form-data" },
    { key: "budget", labelKey: "aiapi.form-budget" },
  ],
  approveGovernedResource: [{ key: "reason", labelKey: "aiapi.form-rationale", required: true }],
  createProviderCandidateGroup: [
    { key: "group", labelKey: "aiapi.form-group", required: true },
    { key: "members", labelKey: "aiapi.form-members" },
  ],
  restoreProviderFromQuarantine: [{ key: "reason", labelKey: "aiapi.form-reason", required: true }],
  setKillSwitch: [{ key: "reason", labelKey: "aiapi.form-reason", required: true }],
  deleteProviderModelCredential: [{ key: "reason", labelKey: "aiapi.form-reason", required: true }],
  retireProviderModelProfile: [{ key: "reason", labelKey: "aiapi.form-reason", required: true }],
  testProviderModelProfile: [],
  "admin:AIAPI-08:ACT-SYSTEM-TEST": [],
  executeProviderRoute: [],
};

function profileFormFields(): FormField[] {
  const fields: FormField[] = [];
  for (const group of AIAPI_PROFILE_FIELD_GROUPS) {
    for (const key of group.fields) {
      const kind: FormField["kind"] =
        key === "capabilityType"
          ? "capability"
          : key === "enabled"
            ? "enabled"
            : key === "supportsReferences"
              ? "yesno"
              : key === "httpMethod"
                ? "method"
                : "text";
      fields.push({
        key,
        labelKey: PROFILE_FIELD_LABELS[key] ?? "aiapi.fld-provider-id",
        required: REQUIRED_PROFILE_FIELDS.has(key),
        kind,
      });
    }
  }
  return fields;
}

const NOTICE_KEYS: Record<string, TranslationKey> = {
  AIAPI_PROFILE_DUPLICATE: "aiapi.notice-duplicate",
  AIAPI_PROFILE_PROVIDER_REQUIRED: "aiapi.notice-provider-required",
  AIAPI_PROFILE_MODEL_REQUIRED: "aiapi.notice-model-required",
  AIAPI_PROFILE_CAPABILITY_INVALID: "aiapi.notice-capability-invalid",
  AIAPI_PROFILE_ADAPTER_REQUIRED: "aiapi.notice-adapter-required",
  AIAPI_PROFILE_BASE_URL_INVALID: "aiapi.notice-base-url-invalid",
  AIAPI_PROFILE_ENDPOINT_REQUIRED: "aiapi.notice-endpoint-required",
  AIAPI_PROFILE_PROMPT_TEMPLATE_INVALID: "aiapi.notice-prompt-template-invalid",
  AIAPI_PROFILE_VERSION_CONFLICT: "aiapi.notice-version-conflict",
  AIAPI_PROFILE_NOT_FOUND: "aiapi.notice-profile-not-found",
  AIAPI_PROFILE_REQUIRED: "aiapi.notice-profile-required",
  AIAPI_CREDENTIAL_REQUIRED: "aiapi.notice-credential-required",
  AIAPI_CREDENTIAL_NOT_SET: "aiapi.notice-credential-not-set",
  AIAPI_SANDBOX_NOT_CONFIGURED: "aiapi.notice-sandbox-not-configured",
  AIAPI_QUEUE_UNAVAILABLE: "aiapi.notice-queue-unavailable",
  AIAPI_TEST_REQUIRED: "aiapi.notice-test-required",
  AIAPI_CAPABILITY_NOT_APPROVED: "aiapi.notice-capability-not-approved",
  AIAPI_DATA_CLASSIFICATION_REQUIRED: "aiapi.notice-data-required",
  AIAPI_KILL_SWITCH_ON: "aiapi.notice-kill-switch-on",
  AIAPI_PROFILE_DISABLED: "aiapi.notice-profile-disabled",
  AIAPI_ADAPTER_UNSUPPORTED: "aiapi.notice-adapter-unsupported",
  AIAPI_PROVIDER_HTTP_ERROR: "aiapi.notice-provider-http-error",
  AIAPI_PROVIDER_TIMEOUT: "aiapi.notice-provider-timeout",
  AIAPI_PROVIDER_UNREACHABLE: "aiapi.notice-provider-unreachable",
  AIAPI_PROVIDER_EMPTY_RESPONSE: "aiapi.notice-provider-empty",
  AIAPI_GOVERNED_REFERENCE_REQUIRED: "aiapi.notice-reference-required",
  AIAPI_CANDIDATE_GROUP_REQUIRED: "aiapi.notice-group-required",
  AIAPI_REASON_REQUIRED: "aiapi.notice-reason-required",
};

const SUCCESS_NOTICE_KEYS: Record<string, TranslationKey> = {
  createProviderModelProfile: "aiapi.notice-created",
  updateProviderModelProfile: "aiapi.notice-saved",
  setProviderModelCredential: "aiapi.notice-credential-saved",
  deleteProviderModelCredential: "aiapi.notice-credential-deleted",
  testProviderModelProfile: "aiapi.notice-test-passed",
  executeProviderRoute: "aiapi.notice-route-executed",
  "admin:AIAPI-08:ACT-SYSTEM-TEST": "aiapi.notice-sandbox-passed",
  retireProviderModelProfile: "aiapi.notice-retired",
  configureGovernedResource: "aiapi.notice-saved",
  approveGovernedResource: "aiapi.notice-saved",
  createProviderCandidateGroup: "aiapi.notice-saved",
  runProviderQueueProbe: "aiapi.notice-queue-probed",
  restoreProviderFromQuarantine: "aiapi.notice-saved",
  setKillSwitch: "aiapi.notice-saved",
  getProviderModelProfile: "aiapi.notice-saved",
  getProviderRouteDecision: "aiapi.notice-saved",
  getProviderQuarantine: "aiapi.notice-saved",
};

function noticeKeyForCode(code?: string): TranslationKey {
  if (code && NOTICE_KEYS[code]) return NOTICE_KEYS[code];
  return "aiapi.notice-rejected";
}

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  danger = false,
  icon,
  gate,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  danger?: boolean;
  icon?: IconName;
  gate?: string;
}) {
  const className = [
    styles.btn,
    primary ? styles.btnPrimary : "",
    danger ? styles.btnDanger : "",
    icon ? styles.iconBtn : "",
  ].filter(Boolean).join(" ");
  const tip = gate && disabled ? `${label} · ${gate}` : label;
  return (
    <button
      type="button"
      className={className}
      data-control-uid={uid}
      data-tip={icon ? tip : undefined}
      aria-label={icon ? tip : undefined}
      title={icon ? undefined : tip}
      disabled={disabled}
      onClick={() => onAct(uid)}
    >
      {icon ? <Icon name={icon} /> : label}
    </button>
  );
}

function Field({ uid, label, value }: { uid: string; label: string; value: string }) {
  return (
    <div className={styles.metric} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Kv({ uid, label, value }: { uid: string; label: string; value: string }) {
  return (
    <div className={styles.kvRow} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function VisualKv({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.kvRow}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ModalForm({
  actionUid,
  title,
  t,
  initial,
  onCancel,
  onSubmit,
}: {
  actionUid: string;
  title: string;
  t: (key: TranslationKey) => string;
  initial?: Record<string, string>;
  onCancel: () => void;
  onSubmit: (value: string) => void;
}) {
  const grouped = actionUid === "createProviderModelProfile" || actionUid === "updateProviderModelProfile";
  const fields = grouped ? profileFormFields() : MODAL_FORMS[actionUid] ?? [];
  const [values, setValues] = useState<Record<string, string>>(() => {
    const seed = { ...(initial ?? {}) };
    if (grouped) {
      if (!seed.promptTemplate) seed.promptTemplate = AIAPI_PROMPT_TEMPLATE_TOKEN;
      if (!seed.enabled) seed.enabled = "ENABLED";
    }
    return seed;
  });
  const canSubmit = fields.every((field) => !field.required || (values[field.key] ?? "").trim().length > 0);

  const update = (key: string, value: string) => setValues((prev) => ({ ...prev, [key]: value }));

  const renderInput = (field: FormField) => {
    const value = values[field.key] ?? "";
    switch (field.kind) {
      case "capability":
        return (
          <select className={styles.formInput} value={value} onChange={(event) => update(field.key, event.target.value)}>
            <option value="">—</option>
            {AIAPI_CAPABILITIES.map((capability) => (
              <option key={capability} value={capability}>
                {capability}
              </option>
            ))}
          </select>
        );
      case "enabled":
        return (
          <select className={styles.formInput} value={value || "ENABLED"} onChange={(event) => update(field.key, event.target.value)}>
            <option value="ENABLED">{t("aiapi.status-enabled")}</option>
            <option value="DISABLED">{t("aiapi.status-disabled")}</option>
          </select>
        );
      case "yesno":
        return (
          <select className={styles.formInput} value={value} onChange={(event) => update(field.key, event.target.value)}>
            <option value="">—</option>
            <option value="YES">{t("aiapi.option-yes")}</option>
            <option value="NO">{t("aiapi.option-no")}</option>
          </select>
        );
      case "method":
        return (
          <select className={styles.formInput} value={value} onChange={(event) => update(field.key, event.target.value)}>
            <option value="">—</option>
            <option value="POST">POST</option>
            <option value="GET">GET</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
          </select>
        );
      case "secret":
        return (
          <input
            className={styles.formInput}
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            value={value}
            onChange={(event) => update(field.key, event.target.value)}
          />
        );
      default:
        return (
          <input
            className={styles.formInput}
            value={value}
            onChange={(event) => update(field.key, event.target.value)}
          />
        );
    }
  };

  const renderField = (field: FormField) => (
    <label key={field.key} className={styles.formRow}>
      <span>
        {t(field.labelKey)}
        {field.required ? " *" : ""}
      </span>
      {renderInput(field)}
    </label>
  );

  return (
    <section className={styles.modal} data-component-uid="AIAPI-01-CMP-MODAL" data-modal-for={actionUid}>
      <h3>{title}</h3>
      <p className={styles.note}>{t("aiapi.modal-hint")}</p>
      {fields.length ? (
        grouped ? (
          <div className={styles.formGroups}>
            {AIAPI_PROFILE_FIELD_GROUPS.map((group) => (
              <fieldset key={group.group} className={styles.formGroup}>
                <legend>{t(group.labelKey)}</legend>
                {fields.filter((field) => (group.fields as readonly string[]).includes(field.key)).map(renderField)}
              </fieldset>
            ))}
          </div>
        ) : (
          <div className={styles.formGrid}>{fields.map(renderField)}</div>
        )
      ) : (
        <p className={styles.note}>{t("aiapi.modal-confirm")}</p>
      )}
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnPrimary}`}
          disabled={!canSubmit}
          onClick={() => onSubmit(JSON.stringify(values))}
        >
          {t("aiapi.submit")}
        </button>
        <button type="button" className={styles.btn} onClick={onCancel}>
          {t("global.common.close")}
        </button>
      </div>
    </section>
  );
}

export function AiapiVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<AiapiFieldValue[]>([]);
  const [view, setView] = useState<AiapiView>("provider_api");
  const [drawerUid, setDrawerUid] = useState<string | null>(null);
  const [modalUid, setModalUid] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [notice, setNotice] = useState<TranslationKey | null>(null);

  const pendingCredential = useRef(false);
  const knownProfileIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchAiapiReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : AIAPI_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof AiapiClientError ? cause.code : "AIAPI_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(AIAPI_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [tick]);

  const act = useCallback(async (controlUid: string, value?: string, successKey?: TranslationKey) => {
    const actionUid = AIAPI_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return false;
    let ok = false;
    try {
      const result = await postAiapiAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, value);
      ok = result.ok;
      setNotice(result.ok ? successKey ?? null : noticeKeyForCode(result.code));
    } catch {
      setNotice("aiapi.notice-rejected");
    }
    setTick((n) => n + 1);
    return ok;
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayAiapiValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(AIAPI_VISIBLE_CONTROLS), []);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );
  const rawValue = useCallback((controlUid: string) => valueOf(controlUid) ?? "", [valueOf]);
  const show = useCallback(
    (controlUid: string) => displayAiapiValue(valueOf(controlUid), loading),
    [valueOf, loading],
  );

  const registryRaw = rawValue(AIAPI_REGISTRY_UID);
  const profiles = useMemo(() => parseProfiles(registryRaw), [registryRaw]);
  const selected = profiles.find((profile) => profile.profileId === selectedProfileId) ?? profiles[0] ?? null;

  useEffect(() => {
    if (!profiles.length) return;
    const ids = new Set(profiles.map((profile) => profile.profileId));
    const added = profiles.find((profile) => !knownProfileIds.current.has(profile.profileId));
    knownProfileIds.current = ids;
    if (added) {
      setSelectedProfileId(added.profileId);
      if (pendingCredential.current) {
        pendingCredential.current = false;
        setView("provider_api");
        setModalUid(SET_CREDENTIAL_UID);
      }
      return;
    }
    if (!ids.has(selectedProfileId)) setSelectedProfileId(profiles[0].profileId);
  }, [profiles, selectedProfileId]);

  const hasProfile = Boolean(selected);
  const credSet = Boolean(selected?.credentialSet);
  const hasAdapter = Boolean(selected?.adapterType);
  const tested = selected?.lastTest === "PASS";
  const hasReference = Boolean(rawValue("AIAPI-01-FLD-PF-REFERENCE"));
  const approved = rawValue("AIAPI-01-FLD-PF-RIGHTS") === "APPROVED";
  const hasData = Boolean(rawValue("AIAPI-01-FLD-PF-DATA"));
  const killOn = rawValue("AIAPI-01-FLD-KILL-SWITCH") === "ON";
  const hasDecision = Boolean(rawValue("AIAPI-01-FLD-ROUTE-DECISION"));
  const quarantine = rawValue("AIAPI-01-FLD-OPS-QUARANTINE");
  const hasQuarantine = Boolean(quarantine) && quarantine !== "RESTORED";

  const gateOf = useCallback(
    (uid: string): { blocked: boolean; reason: string } => {
      switch (AIAPI_CONTROL_ACTIONS[uid]) {
        case "testProviderModelProfile":
          return { blocked: !(hasProfile && credSet && hasAdapter), reason: t("aiapi.gate-test") };
        case "updateProviderModelProfile":
        case "retireProviderModelProfile":
        case "getProviderModelProfile":
          return { blocked: !hasProfile, reason: t("aiapi.gate-profile") };
        case "setProviderModelCredential":
          return { blocked: !hasProfile, reason: t("aiapi.gate-profile") };
        case "deleteProviderModelCredential":
          return { blocked: !credSet, reason: t("aiapi.gate-credential") };
        case "approveGovernedResource":
          return { blocked: !hasReference, reason: t("aiapi.gate-reference") };
        case "executeProviderRoute":
          return {
            blocked: killOn || !(hasProfile && credSet && approved && tested && hasData),
            reason: t("aiapi.gate-route"),
          };
        case "getProviderRouteDecision":
          return { blocked: !hasDecision, reason: t("aiapi.gate-decision") };
        case "getProviderQuarantine":
        case "restoreProviderFromQuarantine":
          return { blocked: !hasQuarantine, reason: t("aiapi.gate-quarantine") };
        case "admin:AIAPI-08:ACT-SYSTEM-TEST":
          return { blocked: !hasProfile, reason: t("aiapi.gate-profile") };
        case "runProviderQueueProbe":
        case "configureGovernedResource":
        case "createProviderCandidateGroup":
        case "setKillSwitch":
          return { blocked: false, reason: "" };
        default:
          return { blocked: false, reason: "" };
      }
    },
    [hasProfile, credSet, hasAdapter, tested, hasReference, approved, hasData, killOn, hasDecision, hasQuarantine, t],
  );

  const gatedDisabled = (uid: string) => disabled || gateOf(uid).blocked;
  const gateReason = (uid: string) => gateOf(uid).reason;

  const selectView = (next: AiapiView, uid: string) => {
    setView(next);
    void act(uid);
  };

  const openDrawer = (uid: string) => {
    setDrawerUid(uid);
    void act(uid);
  };

  const openModal = (uid: string) => setModalUid(uid);

  const submitModal = (value: string) => {
    const uid = modalUid;
    setModalUid(null);
    if (!uid) return;
    const actionUid = AIAPI_CONTROL_ACTIONS[uid];
    let payload = value;
    if (PROFILE_TARGETED_ACTIONS.has(actionUid) && selectedProfileId) {
      try {
        const parsed = JSON.parse(value) as Record<string, unknown>;
        payload = JSON.stringify({ ...parsed, profileId: selectedProfileId });
      } catch {
        payload = value;
      }
    }
    const run = async () => {
      const ok = await act(uid, payload, SUCCESS_NOTICE_KEYS[actionUid]);
      if (ok && actionUid === "createProviderModelProfile") pendingCredential.current = true;
    };
    void run();
  };

  const filteredProfiles = query
    ? profiles.filter((profile) => {
        const haystack = [
          profile.providerId,
          profile.providerName,
          profile.modelId,
          profile.modelName,
          profile.capabilityType,
          profile.adapterType,
          profile.baseUrl,
          profile.endpointPath,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query.toLowerCase());
      })
    : profiles;

  const lastTestCell = (profile: AiapiProfile) =>
    profile.lastTest ? displayAiapiStatus(profile.lastTest, tx, loading) : dash;

  const profileRow = (profile: AiapiProfile) => [
    displayAiapiValue(profile.providerName || profile.providerId, loading),
    displayAiapiValue(profile.modelName || profile.modelId, loading),
    displayAiapiValue(profile.capabilityType, loading),
    displayAiapiValue(profile.adapterType, loading),
    displayAiapiValue(profile.baseUrl, loading),
    displayAiapiValue(profile.endpointPath, loading),
    displayAiapiValue(profile.timeoutSeconds, loading),
    displayAiapiStatus(profile.enabled ? "ENABLED" : "DISABLED", tx, loading),
    displayAiapiStatus(profile.credentialSet ? "SET" : "NOT_SET", tx, loading),
    lastTestCell(profile),
  ];

  const groupValue = (uid: string): string => {
    if (!selected) return dash;
    switch (uid) {
      case "AIAPI-01-PROFILE-GRP-IDENTITY":
        return displayAiapiValue(profileIdentity(selected), loading);
      case "AIAPI-01-PROFILE-GRP-CONNECTION":
        return displayAiapiValue(selected.baseUrl, loading);
      case "AIAPI-01-PROFILE-GRP-ADAPTER":
        return displayAiapiValue(selected.adapterType, loading);
      case "AIAPI-01-PROFILE-GRP-CAPABILITY":
        return displayAiapiValue(selected.capabilityType, loading);
      case "AIAPI-01-PROFILE-GRP-DATA-CONTEXT":
        return displayAiapiValue(selected.endpointPath, loading);
      case "AIAPI-01-PROFILE-GRP-STATUS":
        return displayAiapiStatus(selected.enabled ? "ENABLED" : "DISABLED", tx, loading);
      default:
        return dash;
    }
  };

  const profileValue = (value: string): string => displayAiapiValue(value, loading);

  const selectedField = (uid: string): string => {
    if (!selected) return dash;
    switch (uid) {
      case "AIAPI-01-PRO-DESC-IDENTITY":
        return profileValue(profileIdentity(selected));
      case "AIAPI-01-PRO-DESC-CAPABILITIES":
        return profileValue(profileCapabilities(selected).join(" / "));
      case "AIAPI-01-PRO-DESC-INPUT":
        return profileValue(selected.requestTemplate);
      case "AIAPI-01-PRO-DESC-OUTPUT":
        return profileValue(selected.responseTextPath);
      case "AIAPI-01-PRO-DESC-LIMITS":
        return profileValue(
          [selected.timeoutSeconds ? `${selected.timeoutSeconds}s` : "", selected.maxContext]
            .filter(Boolean)
            .join(" / "),
        );
      case "AIAPI-01-PRO-DESC-ENDPOINT":
        return profileValue([selected.baseUrl, selected.endpointPath, selected.httpMethod].filter(Boolean).join(" · "));
      case "AIAPI-01-PRO-DESC-AUTH":
        return displayAiapiStatus(selected.credentialSet ? "SET" : "NOT_SET", tx, loading);
      case "AIAPI-01-PRO-DESC-HEALTH":
        return selected.lastTest
          ? displayAiapiStatus(selected.lastTest === "PASS" ? "HEALTHY" : "UNKNOWN", tx, loading)
          : dash;
      case "AIAPI-01-PRO-DESC-LAST-TEST":
        return selected.lastTest ? displayAiapiStatus(selected.lastTest, tx, loading) : dash;
      case "AIAPI-01-FLD-OV-PROVIDER":
        return profileValue(selected.providerName || selected.providerId);
      case "AIAPI-01-FLD-OV-CAPABILITY":
        return profileValue(selected.capabilityType);
      case "AIAPI-01-FLD-OV-HEALTH":
        return selected.lastTest
          ? displayAiapiStatus(selected.lastTest === "PASS" ? "HEALTHY" : "UNKNOWN", tx, loading)
          : dash;
      case "AIAPI-01-FLD-OPS-CREDENTIAL":
        return displayAiapiStatus(selected.credentialSet ? "SET" : "NOT_SET", tx, loading);
      case "AIAPI-01-FLD-OPS-HEALTH":
        return selected.lastTest
          ? displayAiapiStatus(selected.lastTest === "PASS" ? "HEALTHY" : "UNKNOWN", tx, loading)
          : dash;
      case "AIAPI-01-PRO-DESC-POSITIONING":
      case "AIAPI-01-PRO-DESC-ACPOS-SCOPE":
      case "AIAPI-01-PRO-DESC-BILLING":
      case "AIAPI-01-PRO-DESC-RECOMMENDED-USE":
      case "AIAPI-01-PRO-DESC-RESTRICTIONS":
      case "AIAPI-01-PRO-DESC-DOCS":
        return dash;
      default:
        return show(uid);
    }
  };

  const modalActionUid = modalUid ? AIAPI_CONTROL_ACTIONS[modalUid] : "";
  const modalInitial = useMemo<Record<string, string> | undefined>(() => {
    if (!selected) return undefined;
    if (modalActionUid === "testProviderModelProfile") return { profileId: selected.profileId };
    if (modalActionUid !== "updateProviderModelProfile") return undefined;
    const initial: Record<string, string> = {
      expectedVersion: String(selected.version),
      providerId: selected.providerId,
      providerName: selected.providerName,
      modelId: selected.modelId,
      modelName: selected.modelName,
      baseUrl: selected.baseUrl,
      endpointPath: selected.endpointPath,
      httpMethod: selected.httpMethod,
      timeoutSeconds: selected.timeoutSeconds,
      adapterType: selected.adapterType,
      requestTemplate: selected.requestTemplate,
      responseTextPath: selected.responseTextPath,
      promptTemplate: selected.promptTemplate || AIAPI_PROMPT_TEMPLATE_TOKEN,
      capabilityType: selected.capabilityType,
      additionalCapabilities: selected.additionalCapabilities,
      supportsReferences: selected.supportsReferences,
      rightsCompatible: selected.rightsCompatible,
      dataClassifications: selected.dataClassifications,
      preferredLanguage: selected.preferredLanguage,
      maxContext: selected.maxContext,
      enabled: selected.enabled ? "ENABLED" : "DISABLED",
    };
    return initial;
  }, [modalActionUid, selected]);

  return (
    <div
      className={styles.page}
      data-page-uid="admin:AIAPI-01"
      data-page-state={pageState}
      data-ui-view={view}
      data-component-count="12"
      data-control-count={visibleUids.size}
      aria-label={tx("aiapi.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("aiapi.error")}
        </div>
      ) : null}

      {notice ? (
        <div className={styles.notice} role="status" data-notice-key={notice}>
          <span>{tx(notice)}</span>
          <button type="button" className={styles.noticeClose} aria-label={tx("global.common.close")} onClick={() => setNotice(null)}>
            {tx("global.common.close")}
          </button>
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="AIAPI-01-CMP-CONTEXT" data-section-uid="AIAPI-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx("aiapi.title")}</h1>
        <p className={styles.headingMeta}>{tx("aiapi.meta")}</p>
      </header>

      <nav className={styles.views} data-section-uid="AIAPI-01-SEC-02" data-component-uid="AIAPI-01-CMP-VIEW-BAR">
        {AIAPI_VIEWS.map((item) => (
          <button
            key={item.uid}
            type="button"
            className={`${styles.viewBtn} ${view === item.key ? styles.viewActive : ""}`}
            data-control-uid={item.uid}
            disabled={disabled}
            onClick={() => selectView(item.key, item.uid)}
          >
            {tx(item.labelKey)}
          </button>
        ))}
      </nav>

      {view === "overview" || view === "provider_api" ? (
        <div className={styles.toolbar} data-component-uid="AIAPI-01-CMP-QUICK-ACTIONS">
          <div className={styles.actions}>
            <Btn
              uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-CREATE-PROFILE"
              label={tx("aiapi.btn-create")}
              onAct={openModal}
              disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-CREATE-PROFILE")}
              primary
            />
            <Btn
              uid={SET_CREDENTIAL_UID}
              label={tx("aiapi.btn-set-key")}
              onAct={openModal}
              disabled={gatedDisabled(SET_CREDENTIAL_UID)}
              gate={gateReason(SET_CREDENTIAL_UID)}
              icon="key"
            />
            <Btn
              uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE"
              label={tx("aiapi.btn-test")}
              onAct={openModal}
              disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE")}
              gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE")}
              icon="plug"
            />
            <Btn
              uid="AIAPI-01-BTN-RUN-SANDBOX-TEST"
              label={tx("aiapi.btn-sandbox")}
              onAct={openModal}
              disabled={gatedDisabled("AIAPI-01-BTN-RUN-SANDBOX-TEST")}
              gate={gateReason("AIAPI-01-BTN-RUN-SANDBOX-TEST")}
              icon="flask"
            />
          </div>
          <input
            className={styles.search}
            data-control-uid="AIAPI-01-FLD-SEARCH"
            disabled={disabled}
            placeholder={tx("aiapi.search-placeholder")}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      ) : null}

      <div className={styles.cols}>
        {view === "overview" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-03" data-component-uid="AIAPI-01-CMP-OVERVIEW">
            <h2>{tx("aiapi.overview-title")}</h2>
            <p className={styles.note}>{tx("aiapi.overview-hint")}</p>
            <div className={styles.statusBar}>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-PROVIDER">
                <span>{tx("aiapi.ov-provider")}</span>
                <strong>{selectedField("AIAPI-01-FLD-OV-PROVIDER")}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-ROUTE">
                <span>{tx("aiapi.ov-route")}</span>
                <strong>{show("AIAPI-01-FLD-OV-ROUTE")}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-CAPABILITY">
                <span>{tx("aiapi.ov-capability")}</span>
                <strong>{selectedField("AIAPI-01-FLD-OV-CAPABILITY")}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-JOB">
                <span>{tx("aiapi.ov-job")}</span>
                <strong>{show("AIAPI-01-FLD-OV-JOB")}</strong>
              </div>
            </div>
            <div className={styles.metricGrid}>
              <Field uid="AIAPI-01-FLD-OV-COST" label={tx("aiapi.ov-cost")} value={show("AIAPI-01-FLD-OV-COST")} />
              <Field uid="AIAPI-01-FLD-OV-HEALTH" label={tx("aiapi.ov-health")} value={selectedField("AIAPI-01-FLD-OV-HEALTH")} />
              <Field uid="AIAPI-01-FLD-OV-INCIDENT" label={tx("aiapi.ov-incident")} value={show("AIAPI-01-FLD-OV-INCIDENT")} />
              <Field uid="AIAPI-01-FLD-OPS-QUEUE" label={tx("aiapi.ops-queue")} value={show("AIAPI-01-FLD-OPS-QUEUE")} />
            </div>
          </section>
        ) : null}

        {view === "provider_api" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-04" data-component-uid="AIAPI-01-CMP-PROVIDER">
            <h2>{tx("aiapi.provider-title")}</h2>
            <p className={styles.note}>{tx("aiapi.provider-hint")}</p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {AIAPI_TABLE_COLUMNS.map((col) => (
                      <th key={col}>{tx(col)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredProfiles.length ? (
                    filteredProfiles.map((profile) => (
                      <tr
                        key={profile.profileId}
                        className={profile.profileId === selectedProfileId ? styles.rowSelected : ""}
                        data-profile-id={profile.profileId}
                        onClick={() => setSelectedProfileId(profile.profileId)}
                      >
                        {profileRow(profile).map((cell, index) => (
                          <td key={AIAPI_TABLE_COLUMNS[index]} title={cell}>
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr className={styles.emptyRow}>
                      <td colSpan={AIAPI_TABLE_COLUMNS.length}>{dash}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className={styles.actions}>
              <Btn
                uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE"
                label={tx("aiapi.btn-view")}
                onAct={openDrawer}
                disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE")}
                gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE")}
                icon="visible"
              />
              <Btn
                uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-UPDATE-PROFILE"
                label={tx("aiapi.btn-edit")}
                onAct={openModal}
                disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-UPDATE-PROFILE")}
                gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-UPDATE-PROFILE")}
                icon="edit"
              />
              <Btn
                uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE"
                label={tx("aiapi.btn-row-test")}
                onAct={openModal}
                disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE")}
                gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE")}
                icon="plug"
              />
              <Btn
                uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-RETIRE-PROFILE"
                label={tx("aiapi.btn-retire")}
                onAct={openModal}
                disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-RETIRE-PROFILE")}
                gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-RETIRE-PROFILE")}
                icon="archive"
              />
              <Btn
                uid={SET_CREDENTIAL_UID}
                label={tx("aiapi.btn-set-key")}
                onAct={openModal}
                disabled={gatedDisabled(SET_CREDENTIAL_UID)}
                gate={gateReason(SET_CREDENTIAL_UID)}
                icon="key"
              />
              <Btn
                uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-DELETE-CREDENTIAL"
                label={tx("aiapi.btn-delete-key")}
                onAct={openModal}
                disabled={gatedDisabled("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-DELETE-CREDENTIAL")}
                gate={gateReason("CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-DELETE-CREDENTIAL")}
                danger
                icon="delete"
              />
            </div>
            <div className={styles.card} data-section-uid="AIAPI-01-SEC-06" data-component-uid="AIAPI-01-CMP-PROFILE-FORM">
              <h3>{tx("aiapi.editor-title")}</h3>
              <p className={styles.note}>{tx("aiapi.editor-hint")}</p>
              <div className={styles.groupGrid}>
                {AIAPI_PROFILE_GROUPS.map((group) => (
                  <div key={group.uid} className={styles.groupChip} data-control-uid={group.uid} title={groupValue(group.uid)}>
                    <span>{tx(group.labelKey)}</span>
                    <em>{groupValue(group.uid)}</em>
                  </div>
                ))}
              </div>
              <div className={styles.actions}>
                <Btn
                  uid="AIAPI-01-BTN-CONFIGURE-GOVERNED-RESOURCE"
                  label={tx("aiapi.btn-configure")}
                  onAct={openModal}
                  disabled={gatedDisabled("AIAPI-01-BTN-CONFIGURE-GOVERNED-RESOURCE")}
                  gate={gateReason("AIAPI-01-BTN-CONFIGURE-GOVERNED-RESOURCE")}
                  icon="sliders"
                />
                <Btn
                  uid="AIAPI-01-BTN-APPROVE-GOVERNED-RESOURCE"
                  label={tx("aiapi.btn-approve")}
                  onAct={openModal}
                  disabled={gatedDisabled("AIAPI-01-BTN-APPROVE-GOVERNED-RESOURCE")}
                  gate={gateReason("AIAPI-01-BTN-APPROVE-GOVERNED-RESOURCE")}
                  icon="check"
                />
              </div>
            </div>
          </section>
        ) : null}

        {view === "routing_test" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-07" data-component-uid="AIAPI-01-CMP-ROUTING">
            <h2>{tx("aiapi.routing-title")}</h2>
            <p className={styles.note}>{hasDecision ? tx("aiapi.flow-decision-hint") : tx("aiapi.empty-routing")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("aiapi.candidate-title")}</h3>
                <p className={styles.note}>{tx("aiapi.candidate-hint")}</p>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-OV-PROVIDER" label={tx("aiapi.col-provider")} value={selectedField("AIAPI-01-FLD-OV-PROVIDER")} />
                  <Kv uid="AIAPI-01-FLD-OV-CAPABILITY" label={tx("aiapi.col-capability")} value={selectedField("AIAPI-01-FLD-OV-CAPABILITY")} />
                  <VisualKv label={tx("aiapi.fld-candidate-group")} value={show("AIAPI-01-FLD-CANDIDATE-GROUP")} />
                </div>
                <Btn
                  uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-CREATE-GROUP"
                  label={tx("aiapi.btn-create-group")}
                  onAct={openModal}
                  disabled={gatedDisabled("CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-CREATE-GROUP")}
                  primary
                />
              </div>
              <div className={styles.card}>
                <h3>{tx("aiapi.preflight-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-PF-CAPABILITY" label={tx("aiapi.pf-capability")} value={show("AIAPI-01-FLD-PF-CAPABILITY")} />
                  <Kv uid="AIAPI-01-FLD-PF-RIGHTS" label={tx("aiapi.pf-rights")} value={show("AIAPI-01-FLD-PF-RIGHTS")} />
                  <Kv uid="AIAPI-01-FLD-PF-DATA" label={tx("aiapi.pf-data")} value={show("AIAPI-01-FLD-PF-DATA")} />
                  <Kv uid="AIAPI-01-FLD-PF-REFERENCE" label={tx("aiapi.pf-reference")} value={show("AIAPI-01-FLD-PF-REFERENCE")} />
                  <Kv uid="AIAPI-01-FLD-PF-BUDGET" label={tx("aiapi.pf-budget")} value={show("AIAPI-01-FLD-PF-BUDGET")} />
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("aiapi.flow-title")}</h3>
              <div className={styles.flow}>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-instruction")}</h4>
                  <p>{tx("aiapi.flow-instruction-hint")}</p>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-compile")}</h4>
                  <p>{tx("aiapi.flow-compile-hint")}</p>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-sandbox")}</h4>
                  <p>{tx("aiapi.flow-sandbox-hint")}</p>
                  <strong>{show("AIAPI-01-FLD-SANDBOX-EVIDENCE")}</strong>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-decision")}</h4>
                  <p>{tx("aiapi.flow-decision-hint")}</p>
                  <strong>{show("AIAPI-01-FLD-ROUTE-DECISION")}</strong>
                </div>
              </div>
              <div className={styles.actions}>
                <Btn
                  uid="CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-EXECUTE-ROUTE"
                  label={tx("aiapi.btn-execute-route")}
                  onAct={openModal}
                  disabled={gatedDisabled("CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-EXECUTE-ROUTE")}
                  gate={gateReason("CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-EXECUTE-ROUTE")}
                  primary
                />
                <Btn
                  uid="AIAPI-01-BTN-RUN-SANDBOX-TEST"
                  label={tx("aiapi.btn-sandbox")}
                  onAct={openModal}
                  disabled={gatedDisabled("AIAPI-01-BTN-RUN-SANDBOX-TEST")}
                  gate={gateReason("AIAPI-01-BTN-RUN-SANDBOX-TEST")}
                  icon="flask"
                />
                <Btn
                  uid="AIAPI-01-BTN-RUN-PROVIDER-QUEUE-PROBE"
                  label={tx("aiapi.btn-queue-probe")}
                  onAct={(uid) => void act(uid, undefined, SUCCESS_NOTICE_KEYS.runProviderQueueProbe)}
                  disabled={gatedDisabled("AIAPI-01-BTN-RUN-PROVIDER-QUEUE-PROBE")}
                  gate={gateReason("AIAPI-01-BTN-RUN-PROVIDER-QUEUE-PROBE")}
                  icon="probe"
                />
                <Btn
                  uid="CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION"
                  label={tx("aiapi.btn-view-decision")}
                  onAct={openDrawer}
                  disabled={gatedDisabled("CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION")}
                  gate={gateReason("CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION")}
                  icon="visible"
                />
              </div>
            </div>
          </section>
        ) : null}

        {view === "operations" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-08" data-component-uid="AIAPI-01-CMP-OPERATIONS">
            <h2>{tx("aiapi.ops-title")}</h2>
            <p className={styles.note}>{tx("aiapi.ops-hint")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("aiapi.job-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-JOB-ID" label={tx("aiapi.field-job-id")} value={show("AIAPI-01-FLD-JOB-ID")} />
                  <Kv uid="AIAPI-01-FLD-JOB-STATUS" label={tx("aiapi.field-job-status")} value={show("AIAPI-01-FLD-JOB-STATUS")} />
                  <Kv uid="AIAPI-01-FLD-ATTEMPT-ID" label={tx("aiapi.field-attempt-id")} value={show("AIAPI-01-FLD-ATTEMPT-ID")} />
                  <Kv uid="AIAPI-01-FLD-CALLBACK" label={tx("aiapi.field-callback")} value={show("AIAPI-01-FLD-CALLBACK")} />
                  <Kv uid="AIAPI-01-FLD-ARTIFACT" label={tx("aiapi.field-artifact")} value={show("AIAPI-01-FLD-ARTIFACT")} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("aiapi.budget-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-OV-COST" label={tx("aiapi.ov-cost")} value={show("AIAPI-01-FLD-OV-COST")} />
                  <Kv uid="AIAPI-01-FLD-OPS-COST" label={tx("aiapi.ops-cost")} value={show("AIAPI-01-FLD-OPS-COST")} />
                  <Kv uid="AIAPI-01-FLD-OPS-INCIDENT" label={tx("aiapi.ops-incident")} value={show("AIAPI-01-FLD-OPS-INCIDENT")} />
                  <Kv uid="AIAPI-01-FLD-OPS-QUEUE" label={tx("aiapi.ops-queue")} value={show("AIAPI-01-FLD-OPS-QUEUE")} />
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <ProfessionalRail
          t={tx}
          show={show}
          field={selectedField}
          disabled={disabled}
          view={view}
          gateOf={gateOf}
          gateReason={gateReason}
          onDrawer={openDrawer}
          onModal={openModal}
          onAct={act}
        />
      </div>

      {drawerUid ? (
        <section className={styles.drawer} data-component-uid="AIAPI-01-CMP-DRAWER">
          <h3>{tx("aiapi.drawer-title")}</h3>
          <p className={styles.note}>{tx("aiapi.drawer-hint")}</p>
          <div className={styles.kvList}>
            <VisualKv label={tx("aiapi.pro-identity")} value={selectedField("AIAPI-01-PRO-DESC-IDENTITY")} />
            <VisualKv label={tx("aiapi.pro-endpoint")} value={selectedField("AIAPI-01-PRO-DESC-ENDPOINT")} />
            <VisualKv label={tx("aiapi.pro-auth")} value={selectedField("AIAPI-01-PRO-DESC-AUTH")} />
            <VisualKv label={tx("aiapi.pro-last-test")} value={selectedField("AIAPI-01-PRO-DESC-LAST-TEST")} />
            <VisualKv label={tx("aiapi.fld-route-decision")} value={show("AIAPI-01-FLD-ROUTE-DECISION")} />
            <VisualKv label={tx("aiapi.ops-quarantine")} value={show("AIAPI-01-FLD-OPS-QUARANTINE")} />
          </div>
          <button type="button" className={styles.btn} onClick={() => setDrawerUid(null)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}

      {modalUid ? (
        <ModalForm
          key={modalUid}
          actionUid={modalActionUid}
          title={tx("aiapi.modal-title")}
          t={tx}
          initial={modalInitial}
          onCancel={() => setModalUid(null)}
          onSubmit={submitModal}
        />
      ) : null}

      {view === "overview" || view === "provider_api" ? null : <div data-component-uid="AIAPI-01-CMP-QUICK-ACTIONS" hidden />}
      {view === "overview" ? null : <div data-component-uid="AIAPI-01-CMP-OVERVIEW" hidden />}
      {view === "provider_api" ? null : <div data-component-uid="AIAPI-01-CMP-PROVIDER" hidden />}
      {view === "provider_api" ? null : <div data-component-uid="AIAPI-01-CMP-PROFILE-FORM" hidden />}
      {view === "routing_test" ? null : <div data-component-uid="AIAPI-01-CMP-ROUTING" hidden />}
      {view === "operations" ? null : <div data-component-uid="AIAPI-01-CMP-OPERATIONS" hidden />}
      {view === "routing_test" || view === "operations" ? null : (
        <div data-component-uid="AIAPI-01-CMP-OPS-RAIL" hidden />
      )}
      {view === "overview" || view === "provider_api" ? null : (
        <div data-component-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION" hidden />
      )}
      {drawerUid ? null : <div data-component-uid="AIAPI-01-CMP-DRAWER" hidden />}
      {modalUid ? null : <div data-component-uid="AIAPI-01-CMP-MODAL" hidden />}
    </div>
  );
}

function ProfessionalRail({
  t,
  show,
  field,
  disabled,
  view,
  gateOf,
  gateReason,
  onDrawer,
  onModal,
  onAct,
}: {
  t: (key: TranslationKey) => string;
  show: (uid: string) => string;
  field: (uid: string) => string;
  disabled: boolean;
  view: AiapiView;
  gateOf: (uid: string) => { blocked: boolean; reason: string };
  gateReason: (uid: string) => string;
  onDrawer: (uid: string) => void;
  onModal: (uid: string) => void;
  onAct: (uid: string) => Promise<boolean>;
}) {
  if (view === "overview" || view === "provider_api") {
    return (
      <aside className={styles.rail} data-section-uid="AIAPI-01-SEC-05" data-component-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION">
        <h2>{t("aiapi.panel-title")}</h2>
        <p className={styles.note}>{t("aiapi.panel-hint")}</p>
        <div className={styles.kvList}>
          {AIAPI_PRO_DESC_FIELDS.map((item) => (
            <Kv key={item.uid} uid={item.uid} label={t(item.labelKey)} value={field(item.uid)} />
          ))}
        </div>
        <div className={styles.actions}>
          <button type="button" className={`${styles.btn} ${styles.btnOk}`} disabled>
            {t("aiapi.badge-no-secret")}
          </button>
          <button type="button" className={styles.btn} disabled>
            {t("aiapi.badge-missing")}
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className={styles.rail} data-section-uid="AIAPI-01-SEC-09" data-component-uid="AIAPI-01-CMP-OPS-RAIL">
      <h2>{t("aiapi.ops-rail-title")}</h2>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-HEALTH">
        <span>{t("aiapi.ops-health")}</span>
        <strong>{field("AIAPI-01-FLD-OPS-HEALTH")}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-CREDENTIAL">
        <span>{t("aiapi.ops-credential")}</span>
        <strong>{field("AIAPI-01-FLD-OPS-CREDENTIAL")}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-QUARANTINE">
        <span>{t("aiapi.ops-quarantine")}</span>
        <strong>{show("AIAPI-01-FLD-OPS-QUARANTINE")}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("aiapi.ops-kill-switch")}</span>
        <strong>{show("AIAPI-01-FLD-KILL-SWITCH")}</strong>
      </div>
      <p className={styles.note}>{t("aiapi.high-risk-hint")}</p>
      <div className={styles.actions}>
        <Btn
          uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE"
          label={t("aiapi.btn-view-quarantine")}
          onAct={onDrawer}
          disabled={disabled || gateOf("CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE").blocked}
          gate={gateReason("CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE")}
          icon="visible"
        />
        <Btn
          uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-RESTORE-PROVIDER"
          label={t("aiapi.btn-restore")}
          onAct={onModal}
          disabled={disabled || gateOf("CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-RESTORE-PROVIDER").blocked}
          gate={gateReason("CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-RESTORE-PROVIDER")}
          danger
          icon="restore"
        />
        <Btn
          uid="CTRL-ADMIN-AIAPI-09-ACT-02-ACT-KILL-SWITCH"
          label={t("aiapi.btn-kill-switch")}
          onAct={onModal}
          disabled={disabled}
          danger
          icon="power"
        />
      </div>
    </aside>
  );
}
