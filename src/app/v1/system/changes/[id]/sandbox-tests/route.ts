import { createSystemRoute } from "@/server/system/systemRouteFactory";
export const POST=createSystemRoute("runSandboxTest",{system_change_id_from:"PATH_ID"});
