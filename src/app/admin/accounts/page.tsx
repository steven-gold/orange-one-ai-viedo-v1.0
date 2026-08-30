import { AppShell } from "@/components/shell/AppShell";
import { IamVisual } from "@/components/pages/IamVisual";
import { IAM_CONTROL_COUNT, IAM_PORTS, IAM_SECTION_COUNT } from "@/domain/iam/iamRuntimeContract";

export default function AccountsPermissionsPage() {
  if (IAM_CONTROL_COUNT !== 14 || IAM_SECTION_COUNT !== 6 || IAM_PORTS.length !== 9) {
    throw new Error("IAM-01 runtime contract is incomplete");
  }
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-02">
      <IamVisual />
    </AppShell>
  );
}
