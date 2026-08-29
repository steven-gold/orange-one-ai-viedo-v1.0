import { AppShell } from "@/components/shell/AppShell";
import { AssetVisual } from "@/components/pages/AssetVisual";

export default function AssetsPage() {
  return (
    <AppShell activeNavId="NAV-03">
      <AssetVisual />
    </AppShell>
  );
}
