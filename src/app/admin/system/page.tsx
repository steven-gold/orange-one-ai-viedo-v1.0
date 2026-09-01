import { AppShell } from "@/components/shell/AppShell";
import { SystemVisual } from "@/components/pages/SystemVisual";
import {
  SYS_CONTROL_REGISTRY,
  SYS_CURRENT_CONTROL_COUNT,
  SYS_SECTION_COUNT,
  SYS_SERVICE_OPERATIONS,
} from "@/domain/system/systemRuntimeContract";

export default function SystemMaintenancePage() {
  if (
    SYS_CURRENT_CONTROL_COUNT !== 12 ||
    SYS_CONTROL_REGISTRY.length !== SYS_CURRENT_CONTROL_COUNT ||
    SYS_SECTION_COUNT !== 8 ||
    SYS_SERVICE_OPERATIONS.length !== 3
  ) {
    throw new Error("SYS-01 runtime contract is incomplete");
  }
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-01">
      <SystemVisual />
    </AppShell>
  );
}
