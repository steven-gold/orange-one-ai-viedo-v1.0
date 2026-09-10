import { AppShell } from "@/components/shell/AppShell";
import { KnowledgeAdminVisual } from "@/components/pages/KnowledgeAdminVisual";

export default function KnowledgeAdminPage() {
  return (
    <AppShell surface="admin">
      <KnowledgeAdminVisual />
    </AppShell>
  );
}
