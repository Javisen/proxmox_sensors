import generatedSnapshot from "./projectSnapshot.generated.json";

export type SnapshotFreshness = "fresh" | "stale" | "unavailable";
export type ReleaseChannel = "Stable" | "Prerelease";
export type RepositoryStatus = "Active" | "Archived";
export type ProjectNoticeLevel = "info" | "warning" | "critical" | "success";

export interface ProjectNoticeData {
  id: string;
  active: boolean;
  level: ProjectNoticeLevel;
  title: string;
  message: string;
  link: string | null;
  linkLabel: string | null;
  startsAt: string | null;
  expiresAt: string | null;
}

export interface SnapshotSource {
  status: SnapshotFreshness;
  url: string;
  checkedAt: string;
  lastSuccessfulAt: string | null;
  error: string | null;
}

export interface ProjectSnapshot {
  schemaVersion: 1;
  freshness: SnapshotFreshness;
  generatedAt: string;
  version: string;
  releasedAt: string;
  releaseChannel: ReleaseChannel;
  hacsListed: boolean;
  stars: number;
  forks: number;
  openIssues: number;
  repositoryStatus: RepositoryStatus;
  repositoryDisabled: boolean;
  notices: ProjectNoticeData[];
  visibleNoticeIds: string[];
  noticeWarnings: string[];
  sources: {
    githubRelease: SnapshotSource;
    githubRepository: SnapshotSource;
    githubIssues: SnapshotSource;
    hacs: SnapshotSource;
    projectNotices: SnapshotSource;
  };
}

export const projectSnapshot = generatedSnapshot as ProjectSnapshot;
