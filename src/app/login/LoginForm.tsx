"use client";

import { useI18n } from "@/i18n/LocaleProvider";

export function LoginForm({ error }: { error: string | null }) {
  const { t } = useI18n();
  return (
    <main className="login-page">
      <form className="login-card" method="post" action="/identity/login" data-page-uid="identity:login">
        <p className="login-brand">ORANGE ONE</p>
        <h1>{t("global.login.title")}</h1>
        <label>
          {t("global.login.email")}
          <input type="text" name="email" autoComplete="username" required />
        </label>
        <label>
          {t("global.login.password")}
          <input type="password" name="password" autoComplete="current-password" required />
        </label>
        {error ? <p className="login-error">{error}</p> : null}
        <button type="submit">{t("global.login.submit")}</button>
      </form>
    </main>
  );
}
