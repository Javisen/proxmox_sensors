import assert from "node:assert/strict";
import test from "node:test";
import {
  DEVELOPMENT_STATUSES,
  normalizeDevelopmentDocument,
} from "./project-development.mjs";

const item = (overrides = {}) => ({
  id: "roadmap-item",
  active: true,
  status: "planned",
  progress: null,
  title: "Roadmap item",
  message: "A roadmap description.",
  ...overrides,
});

const document = (items) => ({ version: "5.2.0", release_status: "planning", items });

test("accepts every supported development status", () => {
  const result = normalizeDevelopmentDocument(document(
    DEVELOPMENT_STATUSES.map((status, index) => item({ id: `item-${index}`, status })),
  ));

  assert.deepEqual(result.items.map(({ status }) => status), DEVELOPMENT_STATUSES);
});

test("preserves inactive items for filtering by the page", () => {
  const result = normalizeDevelopmentDocument(document([item({ active: false })]));
  assert.equal(result.items[0].active, false);
});

test("accepts null and boundary progress values", () => {
  const result = normalizeDevelopmentDocument(document([
    item({ id: "null", progress: null }),
    item({ id: "zero", progress: 0 }),
    item({ id: "middle", progress: 50 }),
    item({ id: "complete", progress: 100 }),
  ]));

  assert.deepEqual(result.items.map(({ progress }) => progress), [null, 0, 50, 100]);
});

test("rejects invalid progress with a comprehensible error", () => {
  assert.throws(
    () => normalizeDevelopmentDocument(document([item({ progress: 101 })])),
    /progress must be null or an integer from 0 to 100/,
  );
});

test("rejects unsupported statuses and duplicate ids", () => {
  assert.throws(
    () => normalizeDevelopmentDocument(document([item({ status: "warning" })])),
    /status must be one of/,
  );
  assert.throws(
    () => normalizeDevelopmentDocument(document([item(), item()])),
    /id must be unique/,
  );
});
