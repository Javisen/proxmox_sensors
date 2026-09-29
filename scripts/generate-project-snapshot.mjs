import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { SOURCE_URLS, createProjectSnapshot, validateSnapshot } from "./project-data.mjs";

const rootDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generatedPath = path.join(rootDirectory, "src/data/projectSnapshot.generated.json");
const fallbackPath = path.join(rootDirectory, "src/data/projectSnapshot.fallback.json");
const noticesPath = path.join(rootDirectory, "website/notices.json");

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

async function readFallback() {
  for (const candidate of [generatedPath, fallbackPath]) {
    try {
      return validateSnapshot(await readJson(candidate));
    } catch {
      // Try the controlled fallback if the generated snapshot is absent or invalid.
    }
  }

  throw new Error("No valid project-data fallback is available");
}

function buildFetch() {
  const forcedFailures = new Set(
    (process.env.PROJECT_DATA_FAIL_SOURCE ?? "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );
  return async (url, options) => {
    const source = url.includes("/releases?")
      ? "githubRelease"
      : url.includes("/search/issues")
        ? "githubIssues"
        : url === SOURCE_URLS.projectNotices
          ? "projectNotices"
          : url.includes("api.github.com/repos/")
            ? "githubRepository"
            : "hacs";

    if (forcedFailures.has(source) || forcedFailures.has("all")) {
      throw new Error(`Simulated ${source} source failure`);
    }

    if (source === "projectNotices") {
      const document = await readJson(noticesPath);
      return {
        ok: true,
        json: async () => document,
      };
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  };
}

const fallback = await readFallback();
const snapshot = await createProjectSnapshot({ fetchImpl: buildFetch(), fallback });

await writeFile(generatedPath, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");

for (const warning of snapshot.noticeWarnings) {
  console.warn(warning);
}

const sourceSummary = Object.entries(snapshot.sources)
  .map(([name, source]) => `${name}=${source.status}`)
  .join(", ");

console.log(`Project snapshot: ${snapshot.freshness} (${sourceSummary})`);
