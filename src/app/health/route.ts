import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  const correlation_id = crypto.randomUUID();
  return NextResponse.json(
    {
      status: "ok",
      service: "ORANGE ONE ACPOS",
      environment: process.env.ACPOS_DEPLOYMENT_ENV ?? "unspecified",
      release_sha: process.env.ACPOS_RELEASE_SHA ?? "unresolved",
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
