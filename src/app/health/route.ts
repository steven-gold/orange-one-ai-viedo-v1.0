import { NextResponse } from "next/server";
import { getDeploymentMetadata } from "@/server/shared/deploymentMetadata";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  const correlation_id = crypto.randomUUID();
  const metadata = getDeploymentMetadata();
  return NextResponse.json(
    {
      status: "ok",
      service: "ORANGE ONE ACPOS",
      environment: metadata.environment,
      release_sha: metadata.release_sha,
      timestamp: new Date().toISOString(),
    },
    {
      status: 200,
      headers: {
        "cache-control": "no-store",
        "x-correlation-id": correlation_id,
      },
    },
  );
}
