#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_PREFIXES = (
    "governance/specifications/current/",
)
PROTECTED_EXACT = {
    "governance/specifications/REGISTRY.yaml",
    "GOVERNANCE_CURRENT.yaml",
}
AUTH_ROOT = "governance/test/spec_change_authorizations"


def git(*args, check=True):
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout


def protected(path):
    return path in PROTECTED_EXACT or any(path.startswith(p) for p in PROTECTED_PREFIXES)


def trailer(message, key):
    prefix = key + ":"
    values = [line[len(prefix):].strip() for line in message.splitlines() if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def prior_authorization_use_exists(auth_uid):
    """Search all reachable refs but exclude exactly the current commit itself."""
    current = git("rev-parse", "HEAD").strip()
    marker = f"Spec-Change-Authorization: {auth_uid}"
    records = git("log", "--all", "--format=%H%x1f%B%x1e")
    for record in records.split("\x1e"):
        record = record.strip("\n")
        if not record or "\x1f" not in record:
            continue
        sha, body = record.split("\x1f", 1)
        if sha.strip() == current:
            continue
        if marker in body:
            return True, sha.strip()
    return False, None


def main():
    if not (ROOT / ".git").exists():
        print("BLOCK: SPEC_MUTATION_GUARD_REQUIRES_GIT_CHECKOUT", file=sys.stderr)
        return 2

    parent_ok = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=ROOT, capture_output=True).returncode == 0
    if not parent_ok:
        print("BLOCK: SPEC_MUTATION_GUARD_REQUIRES_PARENT_COMMIT", file=sys.stderr)
        return 2

    changed = [p for p in git("diff", "--name-only", "HEAD^", "HEAD").splitlines() if p]
    protected_changed = [p for p in changed if protected(p)]
    if not protected_changed:
        print("PASS: no Current Specification / Registry / compatibility-entrypoint mutation in this commit")
        return 0

    message = git("log", "-1", "--pretty=%B")
    auth_uid = trailer(message, "Spec-Change-Authorization")
    scope = trailer(message, "Spec-Change-Scope")
    if not auth_uid or not scope:
        print("BLOCK: protected governance mutation without explicit Spec-Change-Authorization and Spec-Change-Scope trailers", file=sys.stderr)
        print("CHANGED:", *protected_changed, sep="\n- ", file=sys.stderr)
        return 1

    auth_rel = f"{AUTH_ROOT}/{auth_uid}.yaml"
    # Authorization must already exist in the parent commit. It cannot be fabricated in the same commit as the spec mutation.
    parent_auth = git("show", f"HEAD^:{auth_rel}", check=False)
    if not parent_auth:
        print(f"BLOCK: authorization {auth_uid} did not exist in parent commit", file=sys.stderr)
        return 1

    required = (
        f"authorization_uid: {auth_uid}",
        "artifact_type: SPECIFICATION_CHANGE_AUTHORIZATION_RECEIPT",
        "normative_authority: false",
        "authority_source: EXPLICIT_USER_DIRECTIVE",
        "single_use: true",
        "status: APPROVED_FOR_EXACT_SCOPE",
        "ai_may_expand_scope: false",
        "ai_may_reuse_authorization: false",
    )
    missing = [token for token in required if token not in parent_auth]
    if missing:
        print("BLOCK: authorization receipt missing required fail-closed fields", file=sys.stderr)
        for token in missing:
            print("MISSING:", token, file=sys.stderr)
        return 1

    # Single use across all reachable refs, excluding only the exact current commit being evaluated.
    reused, prior_sha = prior_authorization_use_exists(auth_uid)
    if reused:
        print(f"BLOCK: single-use authorization already consumed: {auth_uid} prior_commit={prior_sha}", file=sys.stderr)
        return 1

    # A spec mutation is never justified by construction/test need alone. The receipt is the only admissible authority.
    forbidden_claims = (
        "AUTO_AUTHORIZED_BY_TEST_FAILURE",
        "AUTO_AUTHORIZED_BY_CONSTRUCTION",
        "AUTO_AUTHORIZED_BY_IMPLEMENTATION",
        "AUTO_AUTHORIZED_BY_VERSION_BUMP",
    )
    if any(token in message for token in forbidden_claims):
        print("BLOCK: invalid automatic specification-change authority claim", file=sys.stderr)
        return 1

    print(f"PASS: protected governance mutation authorized by pre-existing explicit user directive {auth_uid}")
    print(f"PASS: authorization scope trailer={scope}")
    print("PASS: protected changed paths:")
    for path in protected_changed:
        print("-", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
