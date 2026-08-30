import { AppShell } from "@/components/shell/AppShell";
import { SystemVisual } from "@/components/pages/SystemVisual";

export default function SystemMaintenancePage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-01">
      <SystemVisual />
    </AppShell>
  );
}
