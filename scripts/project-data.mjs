import {
  normalizeNoticesDocument,
  visibleNoticeIds as computeVisibleNoticeIds,
} from "./project-notices.mjs";

const REPOSITORY = "Javisen/proxmox_sensors";

export const SOURCE_URLS = Object.freeze({
  githubRelease: `https://api.github.com/repos/${REPOSITORY}/releases?per_page=30`,
  githubRepository: `https://api.github.com/repos/${REPOSITORY}`,
  githubIssues: `https://api.github.com/search/issues?q=${encodeURIComponent(
    `repo:${REPOSITORY} is:issue is:open`,
  )}&per_page=1`,
  hacs: "https://raw.githubusercontent.com/hacs/default/master/integration",
  projectNotices: `https://raw.githubusercontent.com/${REPOSITORY}/main/website/notices.json`,
});

const SOURCE_KEYS = Object.freeze(Object.keys(SOURCE_URLS));
const CORE_SOURCE_KEYS = Object.freeze(SOURCE_KEYS.filter((key) => key !== "projectNotices"));

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${field} must be a non-empty string`);
  }

  return value.trim();
}

function isoDate(value, field) {
  const normalized = requiredString(value, field);
  const parsed = new Date(normalized);

  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${field} must be a valid date`);
  }

  return parsed.toISOString();
}

function nonNegativeInteger(value, field) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${field} must be a non-negative integer`);
  }

  return value;
}

function booleanValue(value, field) {
  if (typeof value !== "boolean") {
    throw new Error(`${field} must be a boolean`);
  }

  return value;
}

function normalizeVersion(tagName) {
  return requiredString(tagName, "release.tag_name").replace(/^v(?=\d)/i, "");
}

function hasFallbackValues(snapshot, fields) {
  return isObject(snapshot) && fields.every((field) => snapshot[field] !== null && snapshot[field] !== undefined);
}

function fallbackSource(snapshot, sourceKey, checkedAt, error, available) {
  const previous = isObject(snapshot?.sources?.[sourceKey]) ? snapshot.sources[sourceKey] : {};

  return {
    status: available ? "stale" : "unavailable",
    url: SOURCE_URLS[sourceKey],
    checkedAt,
    lastSuccessfulAt: previous.lastSuccessfulAt ?? null,
    error: error instanceof Error ? error.message : String(error),
  };
}

function freshSource(sourceKey, checkedAt) {
  return {
    status: "fresh",
    url: SOURCE_URLS[sourceKey],
    checkedAt,
    lastSuccessfulAt: checkedAt,
    error: null,
  };
}

async function getJson(fetchImpl, url) {
  const response = await fetchImpl(url, {
    headers: {
      Accept: "application/vnd.github+json, application/json",
      "User-Agent": "proxmox-sensors-web-build",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with HTTP ${response.status}`);
  }

  return response.json();
}

async function fetchRelease(fetchImpl) {
  const releases = await getJson(fetchImpl, SOURCE_URLS.githubRelease);

  if (!Array.isArray(releases)) {
    throw new Error("GitHub releases response must be an array");
  }

  const release = releases.find((item) => isObject(item) && item.draft === false && item.prerelease === false);

  if (!release) {
    throw new Error("No published stable GitHub release was found");
  }

  return {
    version: normalizeVersion(release.tag_name),
    releasedAt: isoDate(release.published_at, "release.published_at"),
    releaseChannel: release.prerelease ? "Prerelease" : "Stable",
  };
}

async function fetchRepository(fetchImpl) {
  const repository = await getJson(fetchImpl, SOURCE_URLS.githubRepository);

  if (!isObject(repository)) {
    throw new Error("GitHub repository response must be an object");
  }

  const archived = booleanValue(repository.archived, "repository.archived");

  return {
    stars: nonNegativeInteger(repository.stargazers_count, "repository.stargazers_count"),
    forks: nonNegativeInteger(repository.forks_count, "repository.forks_count"),
    repositoryStatus: archived ? "Archived" : "Active",
    repositoryDisabled: booleanValue(repository.disabled, "repository.disabled"),
  };
}

async function fetchIssues(fetchImpl) {
  const result = await getJson(fetchImpl, SOURCE_URLS.githubIssues);

  if (!isObject(result) || result.incomplete_results === true) {
    throw new Error("GitHub issue search returned incomplete or invalid results");
  }

  return {
    openIssues: nonNegativeInteger(result.total_count, "issues.total_count"),
  };
}

async function fetchHacs(fetchImpl) {
  const repositories = await getJson(fetchImpl, SOURCE_URLS.hacs);

  if (!Array.isArray(repositories) || repositories.some((entry) => typeof entry !== "string")) {
    throw new Error("HACS catalog response must be a string array");
  }

  return {
    hacsListed: repositories.includes(REPOSITORY),
  };
}

async function fetchProjectNotices(fetchImpl, now) {
  const document = await getJson(fetchImpl, SOURCE_URLS.projectNotices);
  const normalized = normalizeNoticesDocument(document, { now });

  return {
    notices: normalized.notices,
    visibleNoticeIds: normalized.visibleNoticeIds,
    noticeWarnings: normalized.warnings,
  };
}

export function validateSnapshot(snapshot) {
  if (!isObject(snapshot) || snapshot.schemaVersion !== 1) {
    throw new Error("Snapshot schemaVersion must be 1");
  }

  if (!["fresh", "stale", "unavailable"].includes(snapshot.freshness)) {
    throw new Error("Snapshot freshness is invalid");
  }

  isoDate(snapshot.generatedAt, "snapshot.generatedAt");
  requiredString(snapshot.version, "snapshot.version");
  isoDate(snapshot.releasedAt, "snapshot.releasedAt");

  if (!["Stable", "Prerelease"].includes(snapshot.releaseChannel)) {
    throw new Error("Snapshot releaseChannel is invalid");
  }

  booleanValue(snapshot.hacsListed, "snapshot.hacsListed");
  nonNegativeInteger(snapshot.stars, "snapshot.stars");
  nonNegativeInteger(snapshot.forks, "snapshot.forks");
  nonNegativeInteger(snapshot.openIssues, "snapshot.openIssues");

  if (!["Active", "Archived"].includes(snapshot.repositoryStatus)) {
    throw new Error("Snapshot repositoryStatus is invalid");
  }

  booleanValue(snapshot.repositoryDisabled, "snapshot.repositoryDisabled");

  if (!Array.isArray(snapshot.noticeWarnings) || snapshot.noticeWarnings.some((warning) => typeof warning !== "string")) {
    throw new Error("Snapshot noticeWarnings must be a string array");
  }

  const normalizedNotices = normalizeNoticesDocument({ notices: snapshot.notices }, {
    now: new Date(snapshot.generatedAt),
  });
  if (JSON.stringify(normalizedNotices.notices) !== JSON.stringify(snapshot.notices)) {
    throw new Error("Snapshot notices must already be normalized");
  }
  if (JSON.stringify(normalizedNotices.visibleNoticeIds) !== JSON.stringify(snapshot.visibleNoticeIds)) {
    throw new Error("Snapshot visibleNoticeIds do not match its generatedAt time");
  }

  if (!isObject(snapshot.sources)) {
    throw new Error("Snapshot sources must be an object");
  }

  for (const sourceKey of SOURCE_KEYS) {
    const source = snapshot.sources[sourceKey];
    if (!isObject(source) || !["fresh", "stale", "unavailable"].includes(source.status)) {
      throw new Error(`Snapshot source ${sourceKey} is invalid`);
    }
  }

  return snapshot;
}

export async function createProjectSnapshot({ fetchImpl, fallback, now = new Date() }) {
  if (typeof fetchImpl !== "function") {
    throw new Error("A fetch implementation is required");
  }

  const checkedAt = now.toISOString();
  const base = isObject(fallback) ? structuredClone(fallback) : {};
  const snapshot = {
    ...base,
    schemaVersion: 1,
    generatedAt: checkedAt,
    noticeWarnings: Array.isArray(base.noticeWarnings) ? [...base.noticeWarnings] : [],
    sources: { ...(isObject(base.sources) ? base.sources : {}) },
  };

  const requests = {
    githubRelease: {
      fields: ["version", "releasedAt", "releaseChannel"],
      promise: fetchRelease(fetchImpl),
    },
    githubRepository: {
      fields: ["stars", "forks", "repositoryStatus", "repositoryDisabled"],
      promise: fetchRepository(fetchImpl),
    },
    githubIssues: {
      fields: ["openIssues"],
      promise: fetchIssues(fetchImpl),
    },
    hacs: {
      fields: ["hacsListed"],
      promise: fetchHacs(fetchImpl),
    },
    projectNotices: {
      fields: ["notices"],
      promise: fetchProjectNotices(fetchImpl, now),
    },
  };

  const results = await Promise.allSettled(Object.values(requests).map(({ promise }) => promise));

  Object.entries(requests).forEach(([sourceKey, request], index) => {
    const result = results[index];

    if (result.status === "fulfilled") {
      Object.assign(snapshot, result.value);
      snapshot.sources[sourceKey] = freshSource(sourceKey, checkedAt);
      return;
    }

    const hasFallback = hasFallbackValues(base, request.fields);
    const hasSuccessfulNoticeFallback = sourceKey !== "projectNotices"
      || typeof base.sources?.projectNotices?.lastSuccessfulAt === "string";

    snapshot.sources[sourceKey] = fallbackSource(
      base,
      sourceKey,
      checkedAt,
      result.reason,
      hasFallback && hasSuccessfulNoticeFallback,
    );
  });

  snapshot.visibleNoticeIds = computeVisibleNoticeIds(snapshot.notices, now);

  const sourceStates = CORE_SOURCE_KEYS.map((sourceKey) => snapshot.sources[sourceKey].status);
  snapshot.freshness = sourceStates.every((status) => status === "fresh")
    ? "fresh"
    : sourceStates.every((status) => status === "unavailable")
      ? "unavailable"
      : "stale";

  return validateSnapshot(snapshot);
}
