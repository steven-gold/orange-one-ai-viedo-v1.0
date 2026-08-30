import { AppShell } from "@/components/shell/AppShell";
import { StrategyVisual } from "@/components/pages/StrategyVisual";
import { STRATEGY_PORT_COUNT } from "@/domain/strategy/strategyRuntimeContract";

export default function StrategyPage() {
  if (STRATEGY_PORT_COUNT !== 6) {
    throw new Error("STR-01 integration port binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-08">
      <StrategyVisual />
    </AppShell>
  );
}
