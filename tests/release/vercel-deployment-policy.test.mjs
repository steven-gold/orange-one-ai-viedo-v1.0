import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Vercel Git deployment policy only permits main branch", async () => {
  const config = JSON.parse(await readFile("vercel.json", "utf8"));
  assert.deepEqual(config.git?.deploymentEnabled, {
    "*": false,
    main: true,
  });
  assert.deepEqual(config.crons, [
    {
      path: "/v1/internal/queue/provider-execution/drain",
      schedule: "0 0 * * *",
    },
  ]);
});
