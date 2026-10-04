"use client";

import { useEffect } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { displayDashboardValue, isDashboardEmpty } from "./dashboardFormat";
import styles from "./DashboardVisual.module.css";

export interface SectionDrawerProps {
  open: boolean;
  label: string;
  value: string | number | null;
  detail: string;
  loading: boolean;
  onClose: () => void;
}

export function SectionDrawer({ open, label, value, detail, loading, onClose }: SectionDrawerProps) {
  const { t } = useI18n();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const empty = isDashboardEmpty(value, loading);
  return (
    <>
      <button
        type="button"
        className={styles.drawerBackdrop}
        aria-label={t("global.common.close")}
        onClick={onClose}
      />
      <aside className={styles.drawer} role="dialog" aria-label={label}>
        <button type="button" className={styles.drawerClose} onClick={onClose}>
          {t("global.common.close")}
        </button>
        <h2 className={styles.drawerTitle}>{label}</h2>
        <p className={styles.drawerValue}>{displayDashboardValue(value, loading)}</p>
        <p className={styles.drawerDetail}>
          {loading ? t("global.state.empty_value") : empty ? t("global.state.no_data") : detail || t("global.state.no_data")}
        </p>
      </aside>
    </>
  );
}
