"use client";

import { useI18n } from "@/i18n/LocaleProvider";

export function WorkspaceVisual() {
  const { t } = useI18n();
  return (
    <div className="workspace-canvas">
      <header className="workspace-hero">
        <h1>{t("global.shell.workspace")}</h1>
      </header>
      <section className="workspace-row">
        <h2>{t("workspace.row1.title")}</h2>
        <p>{t("workspace.row1.body")}</p>
      </section>
      <section className="workspace-row">
        <h2>{t("workspace.row2.title")}</h2>
        <p>{t("workspace.row2.body")}</p>
      </section>
      <section className="workspace-row">
        <h2>{t("workspace.row3.title")}</h2>
        <p>{t("workspace.row3.body")}</p>
      </section>
    </div>
  );
}
