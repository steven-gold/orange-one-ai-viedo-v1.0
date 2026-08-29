import { CoreVisual } from "@/components/pages/CoreVisual";
import { AppShell } from "@/components/shell/AppShell";

export default function CorePage() {
  return (
    <AppShell activeNavId="NAV-02">
      <CoreVisual />
    </AppShell>
  );
}
