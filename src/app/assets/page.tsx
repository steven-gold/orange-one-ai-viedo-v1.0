import { AppShell } from "@/components/shell/AppShell";
import { AssetVisual } from "@/components/pages/AssetVisual";
import { ASSET_CONTROL_BINDING_COUNT } from "@/domain/asset/assetControlRuntime";

export default function AssetsPage() {
  if (ASSET_CONTROL_BINDING_COUNT !== 85) {
    throw new Error("ASSET-01 control runtime binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-03">
      <AssetVisual />
    </AppShell>
  );
}
