"use client";

import { useState } from "react";
import { LOCALES, LOCALE_LABELS, type TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import styles from "./LoginVisual.module.css";

const REASON_KEYS: Record<string, TranslationKey> = {
  IDENTITY_CREDENTIALS_REJECTED: "login.error.credentials",
  DATABASE_RUNTIME_NOT_BOUND: "login.error.unbound",
  APP_USERS_EMAIL_JOIN_NOT_FOUND: "login.error.unbound_user",
  IDENTITY_SESSION_CREATE_FAILED: "login.error.session",
};

const STEPS = [
  { n: "01", label: "CORE" },
  { n: "02", label: "ASSET" },
  { n: "03", label: "VIDEO" },
  { n: "04", label: "EDIT" },
  { n: "05", label: "QA" },
] as const;

export function LoginVisual({ initialError = "", initialEmail = "" }: { initialError?: string; initialEmail?: string }) {
  const { locale, setLocale, t } = useI18n();
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const reason = initialError in REASON_KEYS ? initialError : "";
  const errorText = reason ? t(REASON_KEYS[reason]) : "";

  return (
    <div className={styles.page} data-surface-uid="identity:login" data-page-state={submitting ? "SUBMITTING" : reason ? "ERROR" : "READY"}>
      <section className={styles.hero} data-component-uid="LOGIN-CMP-01" aria-hidden="true">
        <p className={styles.brand}>ORANGE ONE</p>
        <h1 className={styles.title}>ACPOS</h1>
        <p className={styles.subtitle}>AI CONTENT PRODUCTION OPERATING SYSTEM</p>
        <div className={styles.chain}>
          {STEPS.map((step) => (
            <div key={step.n} className={step.label === "VIDEO" ? `${styles.chip} ${styles.chipActive}` : styles.chip}>
              <span>{step.n}</span>
              <strong>{step.label}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.access}>
        <div className={styles.lang} data-component-uid="LOGIN-CMP-02">
          {LOCALES.map((option) => (
            <button
              key={option}
              type="button"
              className={locale === option ? `${styles.langBtn} ${styles.langBtnOn}` : styles.langBtn}
              aria-pressed={locale === option}
              aria-label={LOCALE_LABELS[option]}
              onClick={() => setLocale(option)}
            >
              {option === "zh-TW" ? t("login.lang.tw") : option === "zh-CN" ? t("login.lang.cn") : "EN"}
            </button>
          ))}
        </div>

        <form
          className={styles.card}
          method="post"
          action="/identity/login"
          onSubmit={() => setSubmitting(true)}
        >
          <p className={styles.cardBrand}>ACPOS</p>
          <h2 className={styles.cardTitle}>{t("login.title")}</h2>
          {errorText ? (
            <p className={styles.error} role="alert" data-component-uid="LOGIN-CMP-03" data-reason={reason}>
              {errorText}
            </p>
          ) : null}
          <label className={styles.label} htmlFor="login-email">
            {t("login.email")}
          </label>
          <input
            id="login-email"
            className={styles.input}
            name="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@example.com"
            data-control-uid="LOGIN-FLD-01"
            disabled={submitting}
          />
          <label className={styles.label} htmlFor="login-password">
            {t("login.password")}
          </label>
          <input
            id="login-password"
            className={styles.input}
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            data-control-uid="LOGIN-FLD-02"
            disabled={submitting}
          />
          <button
            className={styles.submit}
            type="submit"
            data-control-uid="LOGIN-CTL-01"
            disabled={submitting}
          >
            <span>{t("login.submit")}</span>
            <span aria-hidden="true">→</span>
          </button>
        </form>
      </section>
    </div>
  );
}
