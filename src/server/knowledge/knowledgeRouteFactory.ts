import { NextRequest, NextResponse } from "next/server";
import type { KnowledgeOperation } from "@/domain/knowledge/knowledgeRuntimeContract";
import { executeKnowledgePort } from "@/server/knowledge/knowledgeRuntime";

type Ctx = { params: Promise<Record<string, string>> };

function cid(request: NextRequest): string {
  const value = request.headers.get("x-correlation-id");
  return value && value.trim() ? value : crypto.randomUUID();
}

function error(correlation_id: string, status: number, error_uid: string, reason_code: string) {
  return NextResponse.json({ error_uid, reason_code, correlation_id }, { status, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
}

async function run(operation: KnowledgeOperation, request: NextRequest, ctx: Ctx, payload?: unknown) {
  const correlation_id = cid(request);
  const path_params = ctx ? (await ctx.params) ?? {} : {};
  const result = await executeKnowledgePort({ operation, correlation_id, path_params, payload });
  if (!result.ok) return error(correlation_id, result.status, result.error_uid, result.reason_code);
  return NextResponse.json(result.value, { status: 200, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
}

async function jsonPayload(request: NextRequest, correlation_id: string): Promise<{ ok: true; value: unknown } | { ok: false; response: NextResponse }> {
  try { return { ok: true, value: await request.json() }; }
  catch { return { ok: false, response: error(correlation_id, 400, "KB-01-ERR-014", "INVALID_JSON_PAYLOAD") }; }
}

export function knowledgePost(operation: KnowledgeOperation) {
  return async (request: NextRequest, ctx: Ctx) => {
    const correlation_id = cid(request);
    const parsed = await jsonPayload(request, correlation_id);
    if (!parsed.ok) return parsed.response;
    return run(operation, request, ctx, parsed.value);
  };
}

export function knowledgePatch(operation: KnowledgeOperation) {
  return knowledgePost(operation);
}

export function knowledgeGet(operation: KnowledgeOperation) {
  return async (request: NextRequest, ctx: Ctx) => run(operation, request, ctx, undefined);
}
