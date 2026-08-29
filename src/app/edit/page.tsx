import { AppShell } from "@/components/shell/AppShell";
import { EditVisual } from "@/components/pages/EditVisual";

export default function EditPage() {
  return (
    <AppShell activeNavId="NAV-05">
      <EditVisual />
    </AppShell>
  );
}
