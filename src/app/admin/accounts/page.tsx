import { AppShell } from "@/components/shell/AppShell";
import { IamVisual } from "@/components/pages/IamVisual";

export default function AccountsPermissionsPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-02">
      <IamVisual />
    </AppShell>
  );
}
