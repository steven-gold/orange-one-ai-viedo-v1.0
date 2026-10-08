"use client";

import { AssetVisual } from "./AssetVisual";
import { CoreVisual } from "./CoreVisual";
import { DashboardVisual } from "./DashboardVisual";
import { EditVisual } from "./EditVisual";
import { DbVisual } from "./DbVisual";
import { QaVisual } from "./QaVisual";
import { InfoVisual } from "./InfoVisual";
import { StrVisual } from "./StrVisual";
import { VideoVisual } from "./VideoVisual";
import { findPageByUid, type PageAuthority } from "./pageRegistry";
import { useI18n } from "@/i18n/LocaleProvider";

export function WorkspacePage({ pageUid }: { pageUid: string }) {
  const { t } = useI18n();
  const page: PageAuthority | undefined = findPageByUid(pageUid);
  if (!page) {
    return (
      <article className="page-slot" data-page-state="UNRESOLVED">
        <p className="page-slot-reason">{t("global.state.load_failed")}</p>
      </article>
    );
  }
  if (page.pageUid === "workspace:WB-01") {
    return <DashboardVisual />;
  }
  if (page.pageUid === "CORE-01") {
    return <CoreVisual />;
  }
  if (page.pageUid === "ASSET-01") {
    return <AssetVisual />;
  }
  if (page.pageUid === "VIDEO-01") {
    return <VideoVisual />;
  }
  if (page.pageUid === "EDIT-01") {
    return <EditVisual />;
  }
  if (page.pageUid === "QA-01") {
    return <QaVisual />;
  }
  if (page.pageUid === "admin:DB-01") {
    return <DbVisual />;
  }
  if (page.pageUid === "workspace:STR-01") {
    return <StrVisual />;
  }
  if (page.pageUid === "workspace:INFO-01") {
    return <InfoVisual />;
  }
  return (
    <article className="page-slot" data-page-uid={page.pageUid} data-page-state="EMPTY">
      <header className="page-slot-header">
        <h1 className="page-slot-title">{t(page.titleKey)}</h1>
      </header>
      <p className="page-slot-reason">{t("global.page.projection_unbound")}</p>
    </article>
  );
}
