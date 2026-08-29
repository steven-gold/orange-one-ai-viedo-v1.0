import { AppShell } from "@/components/shell/AppShell";
import { QaVisual } from "@/components/pages/QaVisual";

export default function QaPage() {
  return (
    <AppShell activeNavId="NAV-06">
      <QaVisual />
    </AppShell>
  );
}
