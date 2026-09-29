import { createSystemRoute } from "@/server/system/systemRouteFactory";
export const POST=createSystemRoute("createChangeRequest",{system_change_id_from:"PATH_ID"});
