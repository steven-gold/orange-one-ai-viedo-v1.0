import { AppShell } from "@/components/shell/AppShell";
import { ErpVisual } from "@/components/pages/ErpVisual";

export default function ErpFinancePage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-05">
      <ErpVisual />
    </AppShell>
  );
}
