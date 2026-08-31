import type { NextRequest } from "next/server";
import { createCorePostRoute } from "@/server/core/coreRouteFactory";
import { conversationPost } from "@/server/shared/conversationRouteFactory";

const corePost = createCorePostRoute("CORE-01-PORT-MESSAGE-SEND");
const sharedPost = conversationPost("sendConversationMessage");
const CORE_MESSAGE_ACTIONS = new Set(["CORE-01-ACT-SEND", "CORE-01-ACT-MSG-ANALYZE"]);

type RouteContext = { params: Promise<{ conversationId: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const actionUid = request.headers.get("x-core-action-uid");
  if (actionUid && CORE_MESSAGE_ACTIONS.has(actionUid)) {
    return corePost(request, context);
  }
  return sharedPost(request, context);
}
