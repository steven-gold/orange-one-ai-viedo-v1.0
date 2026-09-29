import { createAiApiRoute } from "@/server/aiApi/aiApiRouteFactory";

export const GET = createAiApiRoute("getProviderModelProfile");
export const PATCH = createAiApiRoute("updateProviderModelProfile");
