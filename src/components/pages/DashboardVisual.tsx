"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  DashboardClientError,
  fetchDashboardReadModel,
  openDashboardSection,
  type DashboardSectionValue,
} from "@/lib/client";
import { displayDashboardDetail, displayDashboardValue, isDashboardEmpty } from "./dashboardFormat";
import { DASHBOARD_SECTIONS } from "./dashboardSections";
import { SectionDrawer } from "./SectionDrawer";
import styles from "./DashboardVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";
const PEEK_KEY = "acpos.dashboard.peek";

export function DashboardVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [sections, setSections] = useState<DashboardSectionValue[]>([]);
  const [openSectionUid, setOpenSectionUid] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchDashboardReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setSections(model.sections);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof DashboardClientError ? cause.code : "DASHBOARD_READ_UNAVAILABLE");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [tick]);

  const valueOf = useCallback(
    (sectionUid: string) => sections.find((row) => row.sectionUid === sectionUid),
    [sections],
  );

  const open = useCallback(async (sectionUid: string, controlUid: string) => {
    setOpenSectionUid(sectionUid);
    try {
      await openDashboardSection(DEFAULT_ACCOUNT, sectionUid, controlUid, DEFAULT_SESSION);
    } catch {
      // SECTION_OPEN remains readable even if the audit post is unavailable.
    }
    setTick((n) => n + 1);
  }, []);

  const close = useCallback(() => setOpenSectionUid(null), []);

  useEffect(() => {
    const consumePeek = (componentUid?: string, controlId?: string) => {
      window.sessionStorage.removeItem(PEEK_KEY);
      if (!componentUid || !controlId) return;
      void open(componentUid, controlId);
    };
    const stored = window.sessionStorage.getItem(PEEK_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as { componentUid?: string; controlId?: string };
        consumePeek(parsed.componentUid, parsed.controlId);
      } catch {
        window.sessionStorage.removeItem(PEEK_KEY);
      }
    }
    const onPeek = (event: Event) => {
      const detail = (event as CustomEvent<{ componentUid?: string; controlId?: string }>).detail;
      consumePeek(detail?.componentUid, detail?.controlId);
    };
    window.addEventListener("acpos:dashboard-peek", onPeek);
    return () => window.removeEventListener("acpos:dashboard-peek", onPeek);
  }, [open]);

  const visibleSections = useMemo(() => {
    if (loading || error) return DASHBOARD_SECTIONS;
    if (!authorized) return DASHBOARD_SECTIONS;
    const allowed = new Set(sections.map((row) => row.sectionUid));
    if (allowed.size === 0) return DASHBOARD_SECTIONS;
    return DASHBOARD_SECTIONS.filter((section) => allowed.has(section.componentUid));
  }, [authorized, error, loading, sections]);

  const openDef = DASHBOARD_SECTIONS.find((row) => row.componentUid === openSectionUid);
  const openValue = openSectionUid ? valueOf(openSectionUid) : undefined;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";

  return (
    <div
      className={styles.page}
      data-page-uid="workspace:WB-01"
      data-page-state={pageState}
      data-authority-section-count="14"
      data-authority-control-count="14"
      aria-label={t("wb01.page.name")}
    >
      {error ? (
        <div className={styles.errorBanner} role="alert">
          {t("global.state.load_failed")}
        </div>
      ) : null}
      <div className={styles.grid}>
        {visibleSections.map((section) => {
          const row = valueOf(section.componentUid);
          const value = row?.value ?? null;
          const empty = isDashboardEmpty(value, loading);
          const cardState = loading ? "LOADING" : empty ? "EMPTY" : "READY";
          const detail = displayDashboardDetail(row?.detail ?? "", loading);
          return (
            <section
              key={section.sectionId}
              className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")}
              data-order={section.order}
              data-section-id={section.sectionId}
              data-component-uid={section.componentUid}
              data-state={cardState}
            >
              <header className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>{t(section.titleKey)}</h2>
                <button
                  type="button"
                  className={styles.viewButton}
                  aria-label={t("global.common.view")}
                  data-control-id={section.controlId}
                  onClick={() => void open(section.componentUid, section.controlId)}
                >
                  {t("global.common.view")}
                </button>
              </header>
              <div className={styles.cardBody}>
                <div className={empty || loading ? styles.emptyState : styles.valueState}>
                  {loading ? t("global.state.empty_value") : empty ? t("global.state.no_data") : displayDashboardValue(value, loading)}
                </div>
                {empty || loading || !detail ? null : <p className={styles.cardDetail}>{detail}</p>}
              </div>
            </section>
          );
        })}
      </div>
      <SectionDrawer
        open={Boolean(openDef)}
        label={openDef ? t(openDef.titleKey) : ""}
        value={openValue?.value ?? null}
        detail={openValue?.detail ?? ""}
        loading={loading}
        onClose={close}
      />
    </div>
  );
}
