import { assetDelete,assetPatch } from "@/server/asset/assetRouteFactory";
export const DELETE=assetDelete("ASSET-01-PORT-LAYER-DELETE");
export const PATCH=assetPatch("ASSET-01-PORT-LAYER-PROPS");
