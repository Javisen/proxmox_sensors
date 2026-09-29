import type { NavigationIcon } from "./navigation";
import { projectSnapshot } from "./projectSnapshot";

export type DashboardTone = "neutral" | "success" | "warning" | "pending";

export interface DashboardMetric {
  label: string;
  value: string;
  detail: string;
  tone?: DashboardTone;
  compact?: boolean;
}

export interface QuickLink {
  label: string;
  description: string;
  href: string;
  icon: NavigationIcon;
  external?: boolean;
}

const releaseParts = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
}).formatToParts(new Date(projectSnapshot.releasedAt));
const releasePart = (type: Intl.DateTimeFormatPartTypes) =>
  releaseParts.find((part) => part.type === type)?.value ?? "";
const releaseDate = `${releasePart("day")} ${releasePart("month")} ${releasePart("year")}`;

const snapshotPresentation = {
  fresh: { label: "Public project data", detail: "Current snapshot", tone: "success" as const },
  stale: { label: "Cached project data", detail: "Last known value", tone: "warning" as const },
  unavailable: { label: "Project data unavailable", detail: "No current source", tone: "pending" as const },
}[projectSnapshot.freshness];

const releaseTone = projectSnapshot.releaseChannel === "Stable" ? "success" : "warning";
const hacsTone = projectSnapshot.hacsListed ? "success" : "warning";
const repositoryTone = projectSnapshot.repositoryStatus === "Active" && !projectSnapshot.repositoryDisabled
  ? "success"
  : "warning";

export const homeDashboard = {
  dataLabel: snapshotPresentation.label,
  title: "Proxmox Extended Sensors",
  subtitle: "Home Assistant Integration",
  headerFacts: [
    { label: "Version", value: projectSnapshot.version },
    { label: "Released", value: releaseDate },
    { label: "HACS", value: projectSnapshot.hacsListed ? "Listed" : "Not listed" },
    { label: "GitHub", value: `${projectSnapshot.stars.toLocaleString("en-US")} stars` },
  ],
  status: {
    label: "Status",
    value: projectSnapshot.releaseChannel,
    tone: releaseTone,
  },
  integrationMetrics: [
    {
      label: "Version",
      value: projectSnapshot.version,
      detail: "Stable release",
      tone: snapshotPresentation.tone,
    },
    {
      label: "Released",
      value: releaseDate,
      detail: "GitHub release",
      tone: snapshotPresentation.tone,
      compact: true,
    },
    {
      label: "HACS",
      value: projectSnapshot.hacsListed ? "Listed" : "Not listed",
      detail: "Default catalog",
      tone: hacsTone,
    },
    {
      label: "Status",
      value: projectSnapshot.releaseChannel,
      detail: "Release channel",
      tone: releaseTone,
    },
  ] satisfies DashboardMetric[],
  projectMetrics: [
    {
      label: "GitHub Stars",
      value: projectSnapshot.stars.toLocaleString("en-US"),
      detail: "GitHub repository",
    },
    {
      label: "Forks",
      value: projectSnapshot.forks.toLocaleString("en-US"),
      detail: "GitHub repository",
    },
    {
      label: "Open Issues",
      value: projectSnapshot.openIssues.toLocaleString("en-US"),
      detail: "Pull requests excluded",
    },
    {
      label: "Repository",
      value: projectSnapshot.repositoryStatus,
      detail: projectSnapshot.repositoryDisabled ? "Disabled on GitHub" : "GitHub status",
      tone: repositoryTone,
    },
  ] satisfies DashboardMetric[],
  quickLinks: [
    { label: "Installation", description: "Setup options", href: "/installation/", icon: "install" },
    { label: "Documentation", description: "Guides and reference", href: "/docs/", icon: "docs" },
    { label: "PVE", description: "Proxmox VE section", href: "/pve/", icon: "server" },
    { label: "PBS", description: "Backup Server section", href: "/pbs/", icon: "backup" },
    { label: "Cluster", description: "Cluster section", href: "/cluster/", icon: "cluster" },
    { label: "Dashboard", description: "V5 dashboard section", href: "/dashboard/", icon: "dashboard" },
    {
      label: "GitHub",
      description: "Canonical repository",
      href: "https://github.com/Javisen/proxmox_sensors",
      icon: "github",
      external: true,
    },
  ] satisfies QuickLink[],
};
