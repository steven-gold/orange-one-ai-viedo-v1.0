import { AppShell } from "@/components/shell/AppShell";
import { VideoVisual } from "@/components/pages/VideoVisual";

export default function VideoPage() {
  return (
    <AppShell activeNavId="NAV-04">
      <VideoVisual />
    </AppShell>
  );
}
