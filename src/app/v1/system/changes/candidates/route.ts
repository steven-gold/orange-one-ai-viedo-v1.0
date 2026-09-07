import { createSystemRoute } from "@/server/system/systemRouteFactory";
export const POST=createSystemRoute("createCandidate",{system_change_id_from:"BODY_OPTIONAL"});
