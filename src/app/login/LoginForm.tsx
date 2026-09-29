"use client";

import { LOCALES, LOCALE_LABELS } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";

export function LoginForm({ error }: { error: string | null }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <main className="login-page" data-login-visual="ACPOS_LOGIN_CURRENT_V2">
      <section className="login-hero" aria-hidden="true">
        <div className="login-hero-glow" />
        <div className="login-hero-grid" />
        <div className="login-hero-content">
          <div className="login-brand-lockup">
            <span className="login-brand-wordmark">ORANGE ONE</span>
            <strong className="login-product-name">ACPOS</strong>
          </div>

          <div className="login-pipeline" aria-hidden="true">
            {["CORE", "ASSET", "VIDEO", "EDIT", "QA"].map((stage, index) => (
              <div className="login-pipeline-stage" key={stage}>
                <span className="login-stage-index">{String(index + 1).padStart(2, "0")}</span>
                <span>{stage}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="login-access">
        <div className="login-language-switch" aria-label={t("global.header.language")}>
          {LOCALES.map((candidate) => (
            <button
              key={candidate}
              type="button"
              className={candidate === locale ? "is-active" : ""}
              aria-pressed={candidate === locale}
              onClick={() => setLocale(candidate)}
            >
              {LOCALE_LABELS[candidate]}
            </button>
          ))}
        </div>

        <form
          className="login-card"
          method="post"
          action="/identity/login"
          data-page-uid="identity:login"
          data-login-contract="CURRENT_VISUAL_AUTHORITY"
        >
          <div className="login-card-heading">
            <p className="login-brand">ACPOS</p>
            <h1>{t("global.login.title")}</h1>
          </div>

          <div className="login-field-stack">
            <label>
              <span>{t("global.login.email")}</span>
              <input type="text" name="email" autoComplete="username" required />
            </label>

            <label>
              <span>{t("global.login.password")}</span>
              <input type="password" name="password" autoComplete="current-password" required />
            </label>
          </div>

          {error ? (
            <p className="login-error" role="alert">
              {error}
            </p>
          ) : null}

          <button type="submit" className="login-submit">
            <span>{t("global.login.submit")}</span>
            <span aria-hidden="true">→</span>
          </button>
        </form>
      </section>
    </main>
  );
}
