"use client";

import { AssetVisual } from "./AssetVisual";
import { CoreVisual } from "./CoreVisual";
import { DashboardVisual } from "./DashboardVisual";
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
  return (
    <article className="page-slot" data-page-uid={page.pageUid} data-page-state="EMPTY">
      <header className="page-slot-header">
        <h1 className="page-slot-title">{t(page.titleKey)}</h1>
      </header>
      <p className="page-slot-reason">{t("global.page.projection_unbound")}</p>
    </article>
  );
}
