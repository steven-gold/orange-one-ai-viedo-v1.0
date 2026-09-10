import { AppShell } from "@/components/shell/AppShell";
import { InfoVisual } from "@/components/pages/InfoVisual";
import { INFO_PORT_COUNT } from "@/domain/info/infoRuntimeContract";

export default function InfoPage(){
  if (INFO_PORT_COUNT !== 6) {
    throw new Error("INFO-01 integration port binding incomplete");
  }

  return <AppShell activeNavId="NAV-09"><InfoVisual /></AppShell>;
}
