import { AppShell } from "@/components/shell/AppShell";
import { WorkspaceVisual } from "@/components/pages/WorkspaceVisual";

export const dynamic = "force-dynamic";

export default function CatchAllPage() {
  return (
    <AppShell>
      <WorkspaceVisual />
    </AppShell>
  );
}
