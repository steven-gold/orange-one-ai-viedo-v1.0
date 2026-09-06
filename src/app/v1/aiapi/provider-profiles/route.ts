import { createAiApiRoute } from "@/server/aiApi/aiApiRouteFactory";

export const GET = createAiApiRoute("listProviderModelProfiles");
export const POST = createAiApiRoute("createProviderModelProfile");
