import { DashboardVisual } from "@/components/pages/DashboardVisual";
import { AppShell } from "@/components/shell/AppShell";

export default function Home() {
  return (
    <AppShell activeNavId="NAV-01">
      <DashboardVisual />
    </AppShell>
  );
}
