import { readdir, readFile } from "node:fs/promises";
import { extname, join } from "node:path";

const sourceExtensions = new Set([".ts", ".tsx", ".js", ".jsx", ".json"]);
const forbidden = [
  ["TODO/FIXME/HACK/STUB", /\b(?:TODO|FIXME|HACK|STUB)\b/],
  ["console.log/debug", /console\.(?:log|debug)\s*\(/],
  ["eval", /\beval\s*\(/],
  ["dangerouslySetInnerHTML", /dangerouslySetInnerHTML/],
  ["hardcoded localhost URL", /https?:\/\/(?:127\.0\.0\.1|localhost)/],
  ["OpenAI-style secret", /\bsk-[A-Za-z0-9_-]{20,}\b/],
  ["Groq-style secret", /\bgsk_[A-Za-z0-9_-]{20,}\b/],
  ["Google API key", /\bAIza[A-Za-z0-9_-]{20,}\b/],
  ["private key", /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
];

async function files(root) {
  const output = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) output.push(...(await files(path)));
    else if (sourceExtensions.has(extname(entry.name))) output.push(path);
  }
  return output;
}

const findings = [];
for (const path of await files("src")) {
  const text = await readFile(path, "utf8");
  for (const [label, pattern] of forbidden) {
    if (pattern.test(text)) findings.push(`${label}: ${path}`);
  }
}

if (findings.length) {
  process.stderr.write(`${findings.join("\n")}\n`);
  process.exit(1);
}

process.stdout.write("RELEASE_SOURCE_LINT_PASS\n");
