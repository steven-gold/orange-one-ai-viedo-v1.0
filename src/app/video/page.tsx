import { AppShell } from "@/components/shell/AppShell";
import { VideoVisual } from "@/components/pages/VideoVisual";
import { VIDEO_CONTROL_BINDING_COUNT } from "@/domain/video/videoControlRuntime";

export default function VideoPage() {
  if (VIDEO_CONTROL_BINDING_COUNT !== 85) {
    throw new Error("VIDEO-01 control runtime binding incomplete");
  }

  return (
    <AppShell activeNavId="NAV-04">
      <VideoVisual />
    </AppShell>
  );
}
