import { NextRequest, NextResponse } from "next/server";
import { getUiProjection } from "@/server/shared/uiProjectionRuntime";

function isProductionControlledModeMisconfiguration(): boolean {
  const deploymentEnvironment = (process.env.ACPOS_DEPLOYMENT_ENV ?? "").trim().toLowerCase();
  return deploymentEnvironment === "production" && process.env.NEXT_PUBLIC_ACPOS_RUNTIME_MODE === "CONTROLLED_TEST";
}

export async function GET(request: NextRequest, context: { params: Promise<{ pageUid: string }> }) {
  const current = request.headers.get("x-correlation-id");
  const correlation_id = current && current.trim() ? current : crypto.randomUUID();

  if (isProductionControlledModeMisconfiguration()) {
    return NextResponse.json(
      { reason_code: "UI_PROJECTION_RUNTIME_NOT_BOUND", correlation_id },
      {
        status: 503,
        headers: {
          "x-correlation-id": correlation_id,
          "cache-control": "no-store",
        },
      },
    );
  }

  const { pageUid } = await context.params;
  const result = await getUiProjection({ page_uid: pageUid, correlation_id });
  if (!result.ok) {
    return NextResponse.json(
      { reason_code: result.reason_code, correlation_id },
      {
        status: result.status,
        headers: {
          "x-correlation-id": correlation_id,
          "cache-control": "no-store",
        },
      },
    );
  }

  return NextResponse.json(result.value, {
    status: 200,
    headers: {
      "x-correlation-id": correlation_id,
      "cache-control": "no-store",
    },
  });
}
