import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistFindConversationFile } from "@/server/db/conversationFileStore";
import {
  persistHasAssetPermission,
  persistHasCorePermission,
  persistHasEditPermission,
  persistHasVideoPermission,
} from "@/server/db/persist";
import type { ConversationFilePage } from "@/lib/conversationFile";

export const dynamic = "force-dynamic";

async function pageAllowed(accountUid: string, pageUid: ConversationFilePage): Promise<boolean> {
  if (pageUid === "core") return persistHasCorePermission(accountUid);
  if (pageUid === "asset") return persistHasAssetPermission(accountUid);
  if (pageUid === "video") return persistHasVideoPermission(accountUid);
  return persistHasEditPermission(accountUid);
}

function downloadName(fileName: string): string {
  const trimmed = fileName.trim() || "deliverable.txt";
  return trimmed.replace(/[\r\n"]/g, "_");
}

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const url = new URL(request.url);
    const fileUid = String(url.searchParams.get("fileUid") ?? "").trim();
    const download = url.searchParams.get("download") === "1";
    if (!fileUid.startsWith("FILE-")) {
      return jsonError("CONVERSATION_FILE_UNAVAILABLE", "Unknown conversation file", 404);
    }
    const file = await persistFindConversationFile(fileUid, principal.accountUid);
    if (!file) {
      return jsonError("CONVERSATION_FILE_UNAVAILABLE", "Conversation file not found", 404);
    }
    const allowed = await pageAllowed(principal.accountUid, file.pageUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", "page permission required", 403);
    }
    if (download) {
      const filename = downloadName(file.fileName);
      const encoded = encodeURIComponent(filename);
      return new NextResponse(file.body, {
        status: 200,
        headers: {
          "content-type": file.mimeType || "text/plain; charset=utf-8",
          "content-disposition": `attachment; filename="${filename}"; filename*=UTF-8''${encoded}`,
          "cache-control": "no-store",
        },
      });
    }
    return NextResponse.json({
      fileUid: file.fileUid,
      fileName: file.fileName,
      mimeType: file.mimeType,
      version: file.version,
      updatedAt: file.updatedAt,
      body: file.body,
    });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected conversation file runtime error", 500);
  }
}
