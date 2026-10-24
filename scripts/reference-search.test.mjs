import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  buildReferenceSearchIndex,
  extractPdmReferenceEntries,
  referenceEntryId,
} from "../src/data/referenceSearch.mjs";

const rootDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("builds stable entry links and indexes technical attributes", () => {
  const [entry] = buildReferenceSearchIndex([{
    module: "PVE",
    sectionId: "vm-ct",
    groups: [{
      title: "Virtual Machine Sensors",
      entries: [{
        name: "VM Disk Usage",
        type: "Sensor",
        description: "Root filesystem usage.",
        attributes: ["usage_percent", "root_total_gib"],
      }],
    }],
  }]);

  assert.equal(entry.id, referenceEntryId("PVE", "vm-ct", "Virtual Machine Sensors", "VM Disk Usage"));
  assert.equal(entry.href, `#${entry.id}`);
  assert.match(entry.searchText, /usage_percent/);
  assert.match(entry.searchText, /root_total_gib/);
});

test("derives PDM sensors from repeated documentation terms", () => {
  const entries = extractPdmReferenceEntries([
    { source: "**Datacenter Status** and **Remote Status** sensors.", href: "/docs/pdm/", group: "Overview" },
    { source: "### Datacenter Status\n\n**Datacenter Status** reports `Good`.", href: "/docs/pdm/#monitoring", group: "Monitoring" },
    { source: "### Remote Status\n\n**Remote Status** shows the remote state.", href: "/docs/pdm/#remotes", group: "Remotes" },
    { source: "Use **Settings** to configure it.", href: "/docs/pdm/#configuration", group: "Configuration" },
  ]);

  assert.deepEqual(entries.map((entry) => entry.name), ["Datacenter Status", "Remote Status"]);
  assert.equal(entries[0].href, "/docs/pdm/#datacenter-status");
  assert.deepEqual(entries[0].attributes, []);
  assert.match(entries[0].searchText, /good/);
});

test("built Reference pages expose the predictive combobox in both locales", async () => {
  const english = await readFile(path.join(rootDirectory, "dist/docs/reference/index.html"), "utf8");
  const spanish = await readFile(path.join(rootDirectory, "dist/es/docs/reference/index.html"), "utf8");

  assert.match(english, /role="combobox"/);
  assert.match(english, /role="listbox"/);
  assert.match(english, /"module":"PDM"/);
  assert.match(english, /usage_percent/);
  assert.match(spanish, /Buscar sensores, entidades o atributos/);
  assert.match(spanish, /No hay coincidencias/);
  assert.match(spanish, /\/es\/docs\/pdm\/#datacenter-status/);

  const serializedIndex = english.match(/const searchIndex = (\[.*?\]);\s*const searchCopy/s)?.[1];
  assert.ok(serializedIndex);
  const pdmNames = JSON.parse(serializedIndex)
    .filter((entry) => entry.module === "PDM")
    .map((entry) => entry.name)
    .sort();
  assert.deepEqual(pdmNames, [
    "Datacenter Capacity",
    "Datacenter Inventory",
    "Datacenter Status",
    "Datacenter Updates",
    "Remote Overview",
    "Remote Status",
  ]);
});
