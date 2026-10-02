import type { NavigationAuthority } from "./types";

export const CANONICAL_NAVIGATION_AUTHORITY: NavigationAuthority = {
  authorityUid: "CANONICAL-NAV-AUTHORITY-HOME-001",
  items: [
    { uid: "FRONT-01", area: "FRONT", labelKey: "nav.home", route: "/", order: 1, icon: "H", ariaLabelKey: "nav.home" },
    { uid: "FRONT-02", area: "FRONT", labelKey: "nav.dashboard", route: "/dashboard", order: 2, icon: "D", ariaLabelKey: "nav.dashboard" },
    { uid: "FRONT-03", area: "FRONT", labelKey: "nav.projects", route: "/projects", order: 3, icon: "P", ariaLabelKey: "nav.projects" },
    { uid: "FRONT-04", area: "FRONT", labelKey: "nav.tasks", route: "/tasks", order: 4, icon: "T", ariaLabelKey: "nav.tasks" },
    { uid: "FRONT-05", area: "FRONT", labelKey: "nav.calendar", route: "/calendar", order: 5, icon: "C", ariaLabelKey: "nav.calendar" },
    { uid: "FRONT-06", area: "FRONT", labelKey: "nav.reports", route: "/reports", order: 6, icon: "R", ariaLabelKey: "nav.reports" },
    { uid: "FRONT-07", area: "FRONT", labelKey: "nav.messages", route: "/messages", order: 7, icon: "M", ariaLabelKey: "nav.messages" },
    { uid: "FRONT-08", area: "FRONT", labelKey: "nav.files", route: "/files", order: 8, icon: "F", ariaLabelKey: "nav.files" },
    { uid: "FRONT-09", area: "FRONT", labelKey: "nav.settings", route: "/settings", order: 9, icon: "S", ariaLabelKey: "nav.settings" },
    { uid: "ADMIN-01", area: "ADMIN", labelKey: "admin.overview", route: "/admin/overview", order: 1, icon: "O", ariaLabelKey: "admin.overview" },
    { uid: "ADMIN-02", area: "ADMIN", labelKey: "admin.accounts", route: "/admin/accounts", order: 2, icon: "A", ariaLabelKey: "admin.accounts" },
    { uid: "ADMIN-03", area: "ADMIN", labelKey: "admin.roles", route: "/admin/roles", order: 3, icon: "R", ariaLabelKey: "admin.roles" },
    { uid: "ADMIN-04", area: "ADMIN", labelKey: "admin.permissions", route: "/admin/permissions", order: 4, icon: "P", ariaLabelKey: "admin.permissions" },
    { uid: "ADMIN-05", area: "ADMIN", labelKey: "admin.audit", route: "/admin/audit", order: 5, icon: "L", ariaLabelKey: "admin.audit" },
    { uid: "ADMIN-06", area: "ADMIN", labelKey: "admin.integrations", route: "/admin/integrations", order: 6, icon: "I", ariaLabelKey: "admin.integrations" },
    { uid: "ADMIN-07", area: "ADMIN", labelKey: "admin.storage", route: "/admin/storage", order: 7, icon: "S", ariaLabelKey: "admin.storage" },
    { uid: "ADMIN-08", area: "ADMIN", labelKey: "admin.system", route: "/admin/system", order: 8, icon: "Y", ariaLabelKey: "admin.system" },
    { uid: "ADMIN-09", area: "ADMIN", labelKey: "admin.security", route: "/admin/security", order: 9, icon: "X", ariaLabelKey: "admin.security" },
  ],
};
