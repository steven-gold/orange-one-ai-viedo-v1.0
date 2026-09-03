function readNonEmpty(name: string): string | null {
  const value = process.env[name]?.trim();
  return value ? value : null;
}

export function getDeploymentMetadata(): {
  environment: string;
  release_sha: string;
} {
  return {
    environment: readNonEmpty("ACPOS_DEPLOYMENT_ENV") ?? readNonEmpty("VERCEL_ENV") ?? "unspecified",
    release_sha: readNonEmpty("ACPOS_RELEASE_SHA") ?? readNonEmpty("VERCEL_GIT_COMMIT_SHA") ?? "unresolved",
  };
}
