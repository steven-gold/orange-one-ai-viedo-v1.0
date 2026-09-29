import { AppShell } from "@/components/shell/AppShell";
import { StrategyAdminVisual } from "@/components/pages/StrategyAdminVisual";

export default function StrategyAdminPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-08">
      <StrategyAdminVisual />
    </AppShell>
  );
}
