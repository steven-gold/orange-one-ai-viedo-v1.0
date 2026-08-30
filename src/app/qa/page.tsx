import { AppShell } from "@/components/shell/AppShell";
import { QaVisual } from "@/components/pages/QaVisual";
import { QA_INTEGRATION_PORT_COUNT } from "@/domain/qa/qaRuntimeContract";

export default function QaPage() {
  if (QA_INTEGRATION_PORT_COUNT !== 10) {
    throw new Error("QA-01 integration port binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-06">
      <QaVisual />
    </AppShell>
  );
}
