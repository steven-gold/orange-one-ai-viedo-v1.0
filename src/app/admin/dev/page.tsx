import { AppShell } from "@/components/shell/AppShell";
import { DevVisual } from "@/components/pages/DevVisual";

export default function EnterpriseAutomationPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-03">
      <DevVisual />
    </AppShell>
  );
}
