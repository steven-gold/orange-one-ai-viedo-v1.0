import { eligibleProfiles, type AiapiProfile } from "./aiapiProfiles";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function profile(partial: Partial<AiapiProfile> & Pick<AiapiProfile, "profileId" | "providerId" | "modelId">): AiapiProfile {
  return {
    version: 1,
    providerName: partial.providerId,
    modelName: "",
    baseUrl: "https://example.com/v1",
    endpointPath: "/chat/completions",
    httpMethod: "POST",
    timeoutSeconds: "30",
    adapterType: "openai",
    requestTemplate: "",
    responseTextPath: "choices[0].message.content",
    promptTemplate: "",
    capabilityType: "chat",
    additionalCapabilities: "",
    supportsReferences: "",
    rightsCompatible: "",
    dataClassifications: "",
    preferredLanguage: "",
    maxContext: "",
    enabled: true,
    credentialSet: true,
    lastTest: "",
    lastTestAt: "",
    seq: 1,
    ...partial,
  };
}

{
  const profiles = [
    profile({ profileId: "p1", providerId: "groq", modelId: "a", seq: 1 }),
    profile({ profileId: "p2", providerId: "google", modelId: "b", seq: 2 }),
    profile({ profileId: "p3", providerId: "deepseek", modelId: "c", seq: 3 }),
  ];
  const empty = eligibleProfiles(profiles, "chat", { rights: "", data: "", budget: "" });
  assert(empty.profiles.length === 3, "empty policy still admits configured chat profiles");

  const blocked = eligibleProfiles(profiles, "chat", { rights: "CONFIGURED", data: "INTERNAL", budget: "DEMO" });
  assert(blocked.profiles.length === 0, "non-approved rights still block");

  const approved = eligibleProfiles(profiles, "chat", { rights: "APPROVED", data: "", budget: "" });
  assert(approved.profiles.length === 3, "approved rights admit even without data or budget text");
}

console.log("aiapiProfiles.test.ts PASS");
