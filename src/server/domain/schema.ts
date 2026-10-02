import type { NavigationAuthority } from "./types";

export const CANONICAL_NAVIGATION_AUTHORITY: NavigationAuthority = {
  authorityUid: "CANONICAL-NAV-AUTHORITY-HOME-001",
  items: [
    { uid: "FRONT-01", area: "FRONT", labelKey: "global.nav.dashboard", route: "/", order: 1, icon: "dashboard", ariaLabelKey: "global.nav.dashboard" },
    { uid: "FRONT-02", area: "FRONT", labelKey: "global.nav.project_topic", route: "/core", order: 2, icon: "project", ariaLabelKey: "global.nav.project_topic" },
    { uid: "FRONT-03", area: "FRONT", labelKey: "global.nav.asset", route: "/assets", order: 3, icon: "asset", ariaLabelKey: "global.nav.asset" },
    { uid: "FRONT-04", area: "FRONT", labelKey: "global.nav.video", route: "/video", order: 4, icon: "video", ariaLabelKey: "global.nav.video" },
    { uid: "FRONT-05", area: "FRONT", labelKey: "global.nav.edit_voice", route: "/edit", order: 5, icon: "edit", ariaLabelKey: "global.nav.edit_voice" },
    { uid: "FRONT-06", area: "FRONT", labelKey: "global.nav.qa", route: "/qa", order: 6, icon: "qa", ariaLabelKey: "global.nav.qa" },
    { uid: "FRONT-07", area: "FRONT", labelKey: "global.nav.database", route: "/database", order: 7, icon: "database", ariaLabelKey: "global.nav.database" },
    { uid: "FRONT-08", area: "FRONT", labelKey: "global.nav.strategy", route: "/strategy", order: 8, icon: "strategy", ariaLabelKey: "global.nav.strategy" },
    { uid: "FRONT-09", area: "FRONT", labelKey: "global.nav.latest_information", route: "/info", order: 9, icon: "info", ariaLabelKey: "global.nav.latest_information" },
    { uid: "ADMIN-01", area: "ADMIN", labelKey: "global.admin.system", route: "/admin/system", order: 1, icon: "strategy", ariaLabelKey: "global.admin.system" },
    { uid: "ADMIN-02", area: "ADMIN", labelKey: "global.admin.iam", route: "/admin/accounts", order: 2, icon: "project", ariaLabelKey: "global.admin.iam" },
    { uid: "ADMIN-03", area: "ADMIN", labelKey: "global.admin.dev", route: "/admin/dev", order: 3, icon: "video", ariaLabelKey: "global.admin.dev" },
    { uid: "ADMIN-04", area: "ADMIN", labelKey: "global.admin.social", route: "/admin/social", order: 4, icon: "info", ariaLabelKey: "global.admin.social" },
    { uid: "ADMIN-05", area: "ADMIN", labelKey: "global.admin.erp", route: "/admin/erp", order: 5, icon: "database", ariaLabelKey: "global.admin.erp" },
    { uid: "ADMIN-06", area: "ADMIN", labelKey: "global.admin.aiapi", route: "/admin/aiapi", order: 6, icon: "video", ariaLabelKey: "global.admin.aiapi" },
    { uid: "ADMIN-07", area: "ADMIN", labelKey: "global.admin.qa_criteria", route: "/admin/qa-criteria", order: 7, icon: "qa", ariaLabelKey: "global.admin.qa_criteria" },
    { uid: "ADMIN-08", area: "ADMIN", labelKey: "global.admin.strategy", route: "/admin/strategy", order: 8, icon: "strategy", ariaLabelKey: "global.admin.strategy" },
    { uid: "ADMIN-09", area: "ADMIN", labelKey: "global.admin.knowledge", route: "/admin/knowledge", order: 9, icon: "asset", ariaLabelKey: "global.admin.knowledge" },
  ],
};
