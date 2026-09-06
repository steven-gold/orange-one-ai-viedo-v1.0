import { NextResponse } from "next/server";
import { probeIdentityRuntimeReadiness } from "@/server/identity/identityRuntime";
import { getDeploymentMetadata } from "@/server/shared/deploymentMetadata";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  const correlation_id = crypto.randomUUID();
  if (process.env.NEXT_PUBLIC_ACPOS_RUNTIME_MODE === "CONTROLLED_TEST") {
    return NextResponse.json(
      {
        status: "not_ready",
        reason_code: "CONTROLLED_TEST_NOT_PRODUCTION_READY",
        correlation_id,
      },
      {
        status: 503,
        headers: {
          "cache-control": "no-store",
          "x-correlation-id": correlation_id,
          "retry-after": "30",
        },
      },
    );
  }

  const probe = await probeIdentityRuntimeReadiness();

  if (!probe.ok) {
    return NextResponse.json(
      {
        status: "not_ready",
        reason_code: probe.reason_code,
        correlation_id,
      },
      {
        status: 503,
        headers: {
          "cache-control": "no-store",
          "x-correlation-id": correlation_id,
          "retry-after": "30",
        },
      },
    );
  }

  const metadata = getDeploymentMetadata();
  return NextResponse.json(
    {
      status: "ready",
      service: "ORANGE ONE ACPOS",
      environment: metadata.environment,
      release_sha: metadata.release_sha,
      readiness_scope: "DATABASE_AND_IDENTITY_CONTROL_PLANE",
      ready_account_count: probe.ready_account_count,
      correlation_id,
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
