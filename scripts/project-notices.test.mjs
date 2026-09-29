import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { normalizeNoticesDocument } from "./project-notices.mjs";

const fixtureDirectory = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "fixtures/project-notices",
);
const controlledNow = new Date("2026-09-27T12:00:00.000Z");

async function fixture(name) {
  return JSON.parse(await readFile(path.join(fixtureDirectory, `${name}.json`), "utf8"));
}

test("accepts an empty notices document without rendering notices", async () => {
  const result = normalizeNoticesDocument(await fixture("empty"), { now: controlledNow });
  assert.deepEqual(result.notices, []);
  assert.deepEqual(result.visibleNoticeIds, []);
});

test("makes active warning and critical notices visible", async () => {
  for (const name of ["warning-active", "critical-active"]) {
    const result = normalizeNoticesDocument(await fixture(name), { now: controlledNow });
    assert.equal(result.visibleNoticeIds.length, 1);
  }
});

test("hides future and expired notices at a controlled time", async () => {
  const future = normalizeNoticesDocument(await fixture("future"), { now: controlledNow });
  const expired = normalizeNoticesDocument(await fixture("expired"), { now: controlledNow });
  assert.deepEqual(future.visibleNoticeIds, []);
  assert.deepEqual(expired.visibleNoticeIds, []);
});

test("uses inclusive start and exclusive expiry boundaries", () => {
  const result = normalizeNoticesDocument(
    {
      notices: [
        {
          id: "starts-now",
          active: true,
          level: "info",
          title: "Starts now",
          message: "Visible at the exact start time.",
          startsAt: controlledNow.toISOString(),
        },
        {
          id: "expires-now",
          active: true,
          level: "info",
          title: "Expires now",
          message: "Hidden at the exact expiry time.",
          expiresAt: controlledNow.toISOString(),
        },
        {
          id: "inactive",
          active: false,
          level: "info",
          title: "Inactive",
          message: "Hidden even inside its time window.",
        },
      ],
    },
    { now: controlledNow },
  );

  assert.deepEqual(result.visibleNoticeIds, ["starts-now"]);
});

test("preserves multiple visible notices in source order", async () => {
  const result = normalizeNoticesDocument(await fixture("multiple"), { now: controlledNow });
  assert.deepEqual(result.visibleNoticeIds, ["information", "resolved"]);
});

test("rejects unsupported levels, invalid dates, and duplicate ids", async () => {
  for (const name of ["invalid-level", "invalid-date", "duplicate-id"]) {
    const document = await fixture(name);
    assert.throws(
      () => normalizeNoticesDocument(document, { now: controlledNow }),
      Error,
    );
  }
});

test("omits a non-HTTPS link while preserving the notice", async () => {
  const result = normalizeNoticesDocument(await fixture("invalid-url"), { now: controlledNow });
  assert.equal(result.notices[0].link, null);
  assert.equal(result.notices[0].linkLabel, null);
  assert.equal(result.visibleNoticeIds[0], "invalid-link");
  assert.equal(result.warnings.length, 2);
});
