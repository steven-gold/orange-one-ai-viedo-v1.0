import { createAiApiRoute } from "@/server/aiApi/aiApiRouteFactory";

export const PUT = createAiApiRoute("setProviderModelCredential");
export const DELETE = createAiApiRoute("deleteProviderModelCredential");
