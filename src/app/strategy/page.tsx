import { AppShell } from "@/components/shell/AppShell";
import { StrategyVisual } from "@/components/pages/StrategyVisual";

export default function StrategyPage() {
  return (
    <AppShell activeNavId="NAV-08">
      <StrategyVisual />
    </AppShell>
  );
}
