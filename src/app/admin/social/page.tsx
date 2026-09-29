import { AppShell } from "@/components/shell/AppShell";
import { SocVisual } from "@/components/pages/SocVisual";

export default function SocialPublishingPage() {
  return (
    <AppShell surface="admin" activeNavId="ADMIN-NAV-04">
      <SocVisual />
    </AppShell>
  );
}
