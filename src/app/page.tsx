import { DashboardVisual } from "@/components/pages/DashboardVisual";
import { AppShell } from "@/components/shell/AppShell";
import { DASHBOARD_SECTION_KEYS } from "@/domain/dashboard/readModelContract";

export default function Home() {
  if (DASHBOARD_SECTION_KEYS.length !== 14) {
    throw new Error("WB-01 dashboard section runtime binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-01">
      <DashboardVisual />
    </AppShell>
  );
}
