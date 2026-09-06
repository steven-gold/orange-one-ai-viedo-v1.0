import { NextRequest, NextResponse } from "next/server";
import {
  drainProviderExecutionQueue,
  enqueueQueueRuntimeProbe,
  getProviderExecutionQueueHealth,
} from "@/server/queue/providerExecutionQueueRuntime";

function headers(correlation_id: string) {
  return { "x-correlation-id": correlation_id, "cache-control": "no-store" };
}

export async function GET(req: NextRequest) {
  const correlation_id=req.headers.get("x-correlation-id")?.trim() || crypto.randomUUID();
  const secret=process.env.CRON_SECRET?.trim() ?? "";
  if (!secret) {
    return NextResponse.json(
      { ok:false,reason_code:"QUEUE_CRON_SECRET_NOT_BOUND",correlation_id },
      { status:503,headers:headers(correlation_id) },
    );
  }
  if (req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json(
      { ok:false,reason_code:"QUEUE_CRON_UNAUTHORIZED",correlation_id },
      { status:401,headers:headers(correlation_id) },
    );
  }

  const probe=req.nextUrl.searchParams.get("probe")==="1";
  const idempotency=req.nextUrl.searchParams.get("idempotency_key")?.trim() || undefined;
  const enqueued=probe
    ? await enqueueQueueRuntimeProbe({ correlation_id,idempotency_key:idempotency })
    : null;
  const drained=await drainProviderExecutionQueue(10);
  const health=await getProviderExecutionQueueHealth();
  return NextResponse.json(
    { ok:true,probe:enqueued,drained,health,correlation_id },
    { status:200,headers:headers(correlation_id) },
  );
}
