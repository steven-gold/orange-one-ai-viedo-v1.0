import { AppShell } from "@/components/shell/AppShell";
import { EditVisual } from "@/components/pages/EditVisual";
import { EDIT_INTEGRATION_PORT_COUNT } from "@/domain/edit/editRuntimeContract";

export default function EditPage() {
  if (EDIT_INTEGRATION_PORT_COUNT !== 15) {
    throw new Error("EDIT-01 integration port binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-05">
      <EditVisual />
    </AppShell>
  );
}
