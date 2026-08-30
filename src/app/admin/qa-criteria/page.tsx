import { AppShell } from "@/components/shell/AppShell";
import { QaCriteriaVisual } from "@/components/pages/QaCriteriaVisual";

export default function QaCriteriaPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-07">
      <QaCriteriaVisual />
    </AppShell>
  );
}
