import { CoreVisual } from "@/components/pages/CoreVisual";
import { AppShell } from "@/components/shell/AppShell";
import { CORE_ACTION_UIDS, CORE_PORT_UIDS } from "@/domain/core/coreRuntimeContract";

export default function CorePage() {
  if (CORE_ACTION_UIDS.length !== 34 || CORE_PORT_UIDS.length !== 19) {
    throw new Error("CORE-01 runtime binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-02">
      <CoreVisual />
    </AppShell>
  );
}
