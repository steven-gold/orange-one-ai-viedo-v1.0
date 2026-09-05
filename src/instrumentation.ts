import type { Instrumentation } from "next";
import { emitObservability } from "@/server/shared/observability";

export async function register() {
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }

  const { bindProductionNeonRuntime } = await import("@/server/database/neonRuntime");
  try {
    await bindProductionNeonRuntime();
  } catch {
    // Identity mismatch stays fail-closed; request-path ensure retries with the same reason.
  }
  const { bindWb01ProjectionRuntime } = await import("@/server/dashboard/wb01ProjectionRuntime");
  bindWb01ProjectionRuntime();
}

export const onRequestError: Instrumentation.onRequestError = async (_error, request, context) => {
  const errorRecord = typeof _error === "object" && _error !== null ? (_error as { digest?: unknown }) : {};
  const digest = typeof errorRecord.digest === "string" && errorRecord.digest ? errorRecord.digest : "unresolved";
  const pathname = request.path.split("?", 1)[0] || "/";
  const rawCorrelation = request.headers["x-correlation-id"];
  const correlation_id = typeof rawCorrelation === "string" && rawCorrelation.trim() ? rawCorrelation.trim() : undefined;

  await emitObservability("error", {
    event: "acpos_request_error",
    correlation_id,
    digest,
    method: request.method,
    path: pathname,
    status: 500,
    route_path: context.routePath,
    route_type: context.routeType,
    router_kind: context.routerKind,
    release_sha: process.env.ACPOS_RELEASE_SHA ?? "unresolved",
    outcome: "ERROR",
    reason_code: "UNCAUGHT_SERVER_REQUEST_ERROR",
  });
};
