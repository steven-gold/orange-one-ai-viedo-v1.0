import type { TranslationKey } from "@/i18n/catalog";

export type PageSurface = "front" | "admin";

export interface PageAuthority {
  pageUid: string;
  route: string;
  surface: PageSurface;
  titleKey: TranslationKey;
}

export const PAGE_AUTHORITIES: readonly PageAuthority[] = [
  { pageUid: "workspace:WB-01", route: "/", surface: "front", titleKey: "wb01.page.name" },
  { pageUid: "CORE-01", route: "/core", surface: "front", titleKey: "global.nav.project_topic" },
  { pageUid: "ASSET-01", route: "/assets", surface: "front", titleKey: "global.nav.asset" },
  { pageUid: "VIDEO-01", route: "/video", surface: "front", titleKey: "global.nav.video" },
  { pageUid: "EDIT-01", route: "/edit", surface: "front", titleKey: "global.nav.edit_voice" },
  { pageUid: "QA-01", route: "/qa", surface: "front", titleKey: "global.nav.qa" },
  { pageUid: "admin:DB-01", route: "/db", surface: "front", titleKey: "global.nav.database" },
  { pageUid: "workspace:STR-01", route: "/strategy", surface: "front", titleKey: "global.nav.strategy" },
  { pageUid: "workspace:INFO-01", route: "/info", surface: "front", titleKey: "global.nav.latest_information" },
  { pageUid: "admin:SYS-01", route: "/admin/system", surface: "admin", titleKey: "global.admin.system" },
  { pageUid: "admin:IAM-01", route: "/admin/accounts", surface: "admin", titleKey: "global.admin.iam" },
  { pageUid: "admin:DEV-01", route: "/admin/dev", surface: "admin", titleKey: "global.admin.dev" },
  { pageUid: "admin:SOC-01", route: "/admin/social", surface: "admin", titleKey: "global.admin.social" },
  { pageUid: "admin:ERP-01", route: "/admin/erp", surface: "admin", titleKey: "global.admin.erp" },
  { pageUid: "admin:AIAPI-01", route: "/admin/aiapi", surface: "admin", titleKey: "global.admin.aiapi" },
  { pageUid: "admin:SG-02", route: "/admin/qa-criteria", surface: "admin", titleKey: "global.admin.qa_criteria" },
  { pageUid: "admin:STR-01", route: "/admin/strategy", surface: "admin", titleKey: "global.admin.strategy" },
  { pageUid: "admin:KB-01", route: "/admin/knowledge", surface: "admin", titleKey: "global.admin.knowledge" },
];

export function findPageByUid(pageUid: string | null): PageAuthority | undefined {
  if (!pageUid) return undefined;
  return PAGE_AUTHORITIES.find((page) => page.pageUid === pageUid);
}

export function findPageByRoute(route: string): PageAuthority | undefined {
  return PAGE_AUTHORITIES.find((page) => page.route === route);
}
