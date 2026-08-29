import { AppShell } from "@/components/shell/AppShell";
import { DbVisual } from "@/components/pages/DbVisual";

export default function DatabasePage() {
  return (
    <AppShell activeNavId="NAV-07">
      <DbVisual />
    </AppShell>
  );
}
