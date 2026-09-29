import { AppShell } from "@/components/shell/AppShell";
import { AiApiVisual } from "@/components/pages/AiApiVisual";

export default function AiApiManagementPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-06">
      <AiApiVisual />
    </AppShell>
  );
}
