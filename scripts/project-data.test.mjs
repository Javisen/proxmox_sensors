import assert from "node:assert/strict";
import test from "node:test";
import { createProjectSnapshot, SOURCE_URLS } from "./project-data.mjs";

const checkedAt = "2026-09-27T10:00:00.000Z";
const fallback = {
  schemaVersion: 1,
  freshness: "fresh",
  generatedAt: "2026-09-26T10:00:00.000Z",
  version: "5.1.0",
  releasedAt: "2026-09-26T23:24:50.000Z",
  releaseChannel: "Stable",
  hacsListed: true,
  stars: 67,
  forks: 11,
  openIssues: 1,
  repositoryStatus: "Active",
  repositoryDisabled: false,
  notices: [],
  visibleNoticeIds: [],
  noticeWarnings: [],
  sources: Object.fromEntries(
    Object.entries(SOURCE_URLS).map(([key, url]) => [
      key,
      {
        status: "fresh",
        url,
        checkedAt: "2026-09-26T10:00:00.000Z",
        lastSuccessfulAt: "2026-09-26T10:00:00.000Z",
        error: null,
      },
    ]),
  ),
};

function response(value, ok = true, status = 200) {
  return { ok, status, json: async () => value };
}

test("normalizes official source responses into a fresh snapshot", async () => {
  const fetchImpl = async (url) => {
    if (url === SOURCE_URLS.githubRelease) {
      return response([
        { tag_name: "5.2.0-beta.1", draft: false, prerelease: true, published_at: checkedAt },
        { tag_name: "v5.1.0", draft: false, prerelease: false, published_at: "2026-09-26T23:24:50Z" },
      ]);
    }
    if (url === SOURCE_URLS.githubRepository) {
      return response({ stargazers_count: 70, forks_count: 12, archived: false, disabled: false });
    }
    if (url === SOURCE_URLS.githubIssues) {
      return response({ total_count: 2, incomplete_results: false });
    }
    if (url === SOURCE_URLS.projectNotices) {
      return response({ notices: [] });
    }
    return response(["Javisen/proxmox_sensors"]);
  };

  const snapshot = await createProjectSnapshot({ fetchImpl, fallback, now: new Date(checkedAt) });

  assert.equal(snapshot.freshness, "fresh");
  assert.equal(snapshot.version, "5.1.0");
  assert.equal(snapshot.releaseChannel, "Stable");
  assert.equal(snapshot.stars, 70);
  assert.equal(snapshot.openIssues, 2);
  assert.equal(snapshot.hacsListed, true);
  assert.equal(snapshot.sources.projectNotices.status, "fresh");
  assert.deepEqual(snapshot.notices, []);
  assert.deepEqual(snapshot.visibleNoticeIds, []);
});

test("preserves real fallback values and marks a failed source stale", async () => {
  const fetchImpl = async (url) => {
    if (url === SOURCE_URLS.githubIssues) {
      throw new Error("Simulated GitHub issue-search failure");
    }
    if (url === SOURCE_URLS.githubRelease) {
      return response([{ tag_name: "5.1.0", draft: false, prerelease: false, published_at: fallback.releasedAt }]);
    }
    if (url === SOURCE_URLS.githubRepository) {
      return response({ stargazers_count: 68, forks_count: 11, archived: false, disabled: false });
    }
    if (url === SOURCE_URLS.projectNotices) {
      return response({ notices: [] });
    }
    return response(["Javisen/proxmox_sensors"]);
  };

  const snapshot = await createProjectSnapshot({ fetchImpl, fallback, now: new Date(checkedAt) });

  assert.equal(snapshot.freshness, "stale");
  assert.equal(snapshot.sources.githubIssues.status, "stale");
  assert.equal(snapshot.openIssues, 1);
  assert.equal(snapshot.stars, 68);
});

test("preserves notices and marks their source stale when it is inaccessible", async () => {
  const noticeFallback = structuredClone(fallback);
  noticeFallback.notices = [
    {
      id: "fallback-notice",
      active: true,
      level: "warning",
      title: "Fallback notice",
      message: "Last known valid notice.",
      link: null,
      linkLabel: null,
      startsAt: null,
      expiresAt: null,
    },
  ];
  noticeFallback.visibleNoticeIds = ["fallback-notice"];

  const fetchImpl = async (url) => {
    if (url === SOURCE_URLS.githubRelease) {
      return response([{ tag_name: "5.1.0", draft: false, prerelease: false, published_at: fallback.releasedAt }]);
    }
    if (url === SOURCE_URLS.githubRepository) {
      return response({ stargazers_count: 67, forks_count: 11, archived: false, disabled: false });
    }
    if (url === SOURCE_URLS.githubIssues) {
      return response({ total_count: 1, incomplete_results: false });
    }
    if (url === SOURCE_URLS.projectNotices) {
      throw new Error("Simulated notices source failure");
    }
    return response(["Javisen/proxmox_sensors"]);
  };

  const snapshot = await createProjectSnapshot({ fetchImpl, fallback: noticeFallback, now: new Date(checkedAt) });

  assert.equal(snapshot.freshness, "fresh");
  assert.equal(snapshot.sources.projectNotices.status, "stale");
  assert.deepEqual(snapshot.visibleNoticeIds, ["fallback-notice"]);
  assert.equal(snapshot.notices[0].message, "Last known valid notice.");
});

test("marks notices unavailable when no successful canonical snapshot exists", async () => {
  const unavailableFallback = structuredClone(fallback);
  unavailableFallback.sources.projectNotices.status = "unavailable";
  unavailableFallback.sources.projectNotices.lastSuccessfulAt = null;

  const fetchImpl = async (url) => {
    if (url === SOURCE_URLS.githubRelease) {
      return response([{ tag_name: "5.1.0", draft: false, prerelease: false, published_at: fallback.releasedAt }]);
    }
    if (url === SOURCE_URLS.githubRepository) {
      return response({ stargazers_count: 67, forks_count: 11, archived: false, disabled: false });
    }
    if (url === SOURCE_URLS.githubIssues) {
      return response({ total_count: 1, incomplete_results: false });
    }
    if (url === SOURCE_URLS.projectNotices) {
      throw new Error("Simulated notices source failure");
    }
    return response(["Javisen/proxmox_sensors"]);
  };

  const snapshot = await createProjectSnapshot({
    fetchImpl,
    fallback: unavailableFallback,
    now: new Date(checkedAt),
  });

  assert.equal(snapshot.freshness, "fresh");
  assert.equal(snapshot.sources.projectNotices.status, "unavailable");
  assert.deepEqual(snapshot.notices, []);
});

test("uses the last valid notices snapshot when the canonical document is invalid", async () => {
  const invalidSourceFallback = structuredClone(fallback);
  invalidSourceFallback.notices = [
    {
      id: "last-valid-notice",
      active: true,
      level: "info",
      title: "Last valid notice",
      message: "Preserved after invalid canonical data.",
      link: null,
      linkLabel: null,
      startsAt: null,
      expiresAt: null,
    },
  ];
  invalidSourceFallback.visibleNoticeIds = ["last-valid-notice"];

  const fetchImpl = async (url) => {
    if (url === SOURCE_URLS.githubRelease) {
      return response([{ tag_name: "5.1.0", draft: false, prerelease: false, published_at: fallback.releasedAt }]);
    }
    if (url === SOURCE_URLS.githubRepository) {
      return response({ stargazers_count: 67, forks_count: 11, archived: false, disabled: false });
    }
    if (url === SOURCE_URLS.githubIssues) {
      return response({ total_count: 1, incomplete_results: false });
    }
    if (url === SOURCE_URLS.projectNotices) {
      return response({ notices: [{ id: "invalid" }] });
    }
    return response(["Javisen/proxmox_sensors"]);
  };

  const snapshot = await createProjectSnapshot({
    fetchImpl,
    fallback: invalidSourceFallback,
    now: new Date(checkedAt),
  });

  assert.equal(snapshot.sources.projectNotices.status, "stale");
  assert.deepEqual(snapshot.visibleNoticeIds, ["last-valid-notice"]);
  assert.equal(snapshot.notices[0].message, "Preserved after invalid canonical data.");
});
