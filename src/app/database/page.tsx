import { AppShell } from "@/components/shell/AppShell";
import { DbVisual } from "@/components/pages/DbVisual";
import { DB_PORT_COUNT } from "@/domain/database/dbRuntimeContract";

export default function DatabasePage() {
  if (DB_PORT_COUNT !== 7) {
    throw new Error("DB-01 read model port binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-07">
      <DbVisual />
    </AppShell>
  );
}
