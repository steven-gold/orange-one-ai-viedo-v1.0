import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureCoreProjectionResolver, type CoreNormalizedProjection } from "@/domain/core/coreProjectionAdapter";
import { configureAssetProjectionResolver, type AssetNormalizedProjection } from "@/domain/asset/assetProjectionPort";
import { configureVideoProjectionResolver, type VideoNormalizedProjection } from "@/domain/video/videoProjectionPort";
import { configureEditProjectionResolver } from "@/domain/edit/editProjectionPort";
import type { EditResolvedContext } from "@/domain/edit/editClientState";
import { configureIamProjectionResolver, type IamNormalizedProjection } from "@/domain/iam/iamClientPort";
import { configureInfoProjectionResolver, type InfoNormalizedProjection } from "@/domain/info/infoProjectionPort";
import { configureDevProjectionResolver, type DevNormalizedProjection } from "@/domain/dev/devProjectionPort";
import { bindIdentityClientCommandAdapters } from "@/domain/catalog/identityClientCommandAdapters";
import { configureStrategyProjectionResolver, type StrategyNormalizedProjection } from "@/domain/strategy/strategyProjectionPort";
import { configureAiApiProjectionResolver, type AiApiProjection } from "@/domain/aiApi/aiApiRuntimePort";
import { configureStrategyAdminProjectionResolver, type StrategyAdminProjection } from "@/domain/strategyAdmin/strategyAdminRuntimePort";

let bound = false;

function asObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("IDENTITY_PROJECTION_NOT_OBJECT");
  }
  return value as Record<string, unknown>;
}

export function bindIdentityClientProjectionAdapters(): void {
  if (bound || isControlledTestMode()) return;
  bound = true;
  bindIdentityClientCommandAdapters();
  configureCoreProjectionResolver({
    resolve: (raw) => asObject(raw) as CoreNormalizedProjection,
  });
  configureAssetProjectionResolver({
    resolve: (raw) => asObject(raw) as AssetNormalizedProjection,
  });
  configureVideoProjectionResolver({
    resolve: (raw) => asObject(raw) as VideoNormalizedProjection,
  });
  configureEditProjectionResolver({
    resolve: (raw) => asObject(raw) as EditResolvedContext,
  });
  configureIamProjectionResolver({
    resolve: (raw) => asObject(raw) as IamNormalizedProjection,
  });
  configureInfoProjectionResolver({
    resolve: (raw) => asObject(raw) as InfoNormalizedProjection,
  });
  configureDevProjectionResolver({
    resolve: (raw) => asObject(raw) as DevNormalizedProjection,
  });
  configureStrategyProjectionResolver({
    resolve: (raw) => asObject(raw) as StrategyNormalizedProjection,
  });
  configureAiApiProjectionResolver({
    resolve: (raw) => asObject(raw) as AiApiProjection,
  });
  configureStrategyAdminProjectionResolver({
    resolve: (raw) => asObject(raw) as StrategyAdminProjection,
  });
}
