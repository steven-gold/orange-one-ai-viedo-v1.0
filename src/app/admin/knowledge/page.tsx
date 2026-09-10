import { AppShell } from "@/components/shell/AppShell";
import { KnowledgeAdminVisual } from "@/components/pages/KnowledgeAdminVisual";

export default function KnowledgeAdminPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-09">
      <KnowledgeAdminVisual />
    </AppShell>
  );
}
