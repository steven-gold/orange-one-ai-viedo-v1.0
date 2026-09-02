import type { Instrumentation } from "next";

export function register() {}

export const onRequestError: Instrumentation.onRequestError = async (_error, request, context) => {
  const errorRecord = typeof _error === "object" && _error !== null ? (_error as { digest?: unknown }) : {};
  const digest = typeof errorRecord.digest === "string" && errorRecord.digest ? errorRecord.digest : "unresolved";
  const pathname = request.path.split("?", 1)[0] || "/";
  const record = {
    event: "acpos_request_error",
    digest,
    method: request.method,
    path: pathname,
    route_path: context.routePath,
    route_type: context.routeType,
    router_kind: context.routerKind,
    release_sha: process.env.ACPOS_RELEASE_SHA ?? "unresolved",
    timestamp: new Date().toISOString(),
  };
  console.error(JSON.stringify(record));
};
