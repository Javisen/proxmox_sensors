import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const rootDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distDirectory = path.join(rootDirectory, "dist");

const routeFiles = [
  "index.html",
  "cluster/index.html",
  "dashboard/index.html",
  "development/index.html",
  "docs/index.html",
  "docs/cluster/index.html",
  "docs/dashboard/index.html",
  "docs/getting-started/index.html",
  "docs/pbs/index.html",
  "docs/pdm/index.html",
  "docs/pve/index.html",
  "docs/reference/index.html",
  "installation/index.html",
  "pbs/index.html",
  "pdm/index.html",
  "pve/index.html",
];

const readRoute = (route) => readFile(path.join(distDirectory, route), "utf8");

test("builds every English route and its Spanish fallback without duplicate page sources", async () => {
  for (const route of routeFiles) {
    await stat(path.join(distDirectory, route));
    await stat(path.join(distDirectory, "es", route));
  }

  await assert.rejects(stat(path.join(rootDirectory, "src/pages/es")));
});

test("emits locale metadata, canonical alternates and localized navigation", async () => {
  const english = await readRoute("index.html");
  const spanish = await readRoute("es/index.html");

  assert.match(english, /<html lang="en"/);
  assert.match(spanish, /<html lang="es"/);
  assert.match(spanish, /rel="canonical" href="https:\/\/proxmox-sensors\.es\/"/);
  assert.match(spanish, /hreflang="es" href="https:\/\/proxmox-sensors\.es\/es\/"/);
  assert.match(spanish, />Inicio</);
  assert.match(spanish, />Documentación</);
  assert.match(spanish, /href="\/es\/pve\/"/);
  assert.match(spanish, /href="\/" hreflang="en"/);
});

test("ships the centralized Spanish page catalog on localized routes", async () => {
  const spanish = await readRoute("es/index.html");

  assert.match(spanish, /Estadísticas del proyecto/);
  assert.match(spanish, /Resumen de la integración/);
  assert.match(spanish, /Ver todos en GitHub/);
});

test("renders Development and Notices from their JSON translations", async () => {
  const englishDevelopment = await readRoute("development/index.html");
  const spanishDevelopment = await readRoute("es/development/index.html");
  const englishHome = await readRoute("index.html");
  const spanishHome = await readRoute("es/index.html");

  assert.match(englishDevelopment, /VM\/LXC Migration Reliability/);
  assert.match(spanishDevelopment, /Fiabilidad de la migración de VM\/LXC/);
  assert.match(englishHome, /Proxmox Extended Sensors V5\.2\.0 Released!/);
  assert.match(spanishHome, /¡Proxmox Extended Sensors V5\.2\.0 ya disponible!/);
});
