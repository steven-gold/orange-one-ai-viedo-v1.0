import { AppShell } from "@/components/shell/AppShell";

export const dynamic = "force-dynamic";

export default async function CatchAllPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const initialRoute = `/${slug.join("/")}`;
  return <AppShell initialRoute={initialRoute} />;
}
