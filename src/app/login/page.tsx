"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";

export default function LoginPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/v1/identity/session", {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setError(typeof record.reason_code === "string" ? record.reason_code : t("global.login.failed"));
        setBusy(false);
        return;
      }
      window.location.assign("/");
    } catch {
      setError(t("global.login.failed"));
      setBusy(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit} data-page-uid="identity:login">
        <p className="login-brand">ORANGE ONE</p>
        <h1>{t("global.login.title")}</h1>
        <label>
          {t("global.login.email")}
          <input
            type="email"
            name="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          {t("global.login.password")}
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? <p className="login-error">{error}</p> : null}
        <button type="submit" disabled={busy}>
          {t("global.login.submit")}
        </button>
      </form>
    </main>
  );
}
