import type { NavigationIcon } from "./navigation";

export interface DocumentationTopic {
  title: string;
  description: string;
}

export interface DocumentationCategory {
  slug: string;
  title: string;
  href: string;
  icon: NavigationIcon;
  summary: string;
  introduction: string;
  topics: DocumentationTopic[];
}

export const documentationCategories: DocumentationCategory[] = [
  {
    slug: "getting-started",
    title: "Getting Started",
    href: "/docs/getting-started/",
    icon: "home",
    summary: "Practical guidance and recommended practices for getting the most from the integration.",
    introduction: "Proxmox Extended Sensors can expose a large amount of information from your Proxmox environment, but a useful Home Assistant setup does not need to monitor everything. This guide introduces a practical way to decide what to connect, what to monitor and how to turn that information into something useful for everyday operation.",
    topics: [
      { title: "Platform orientation", description: "Understand where PVE, PBS and cluster-wide information fit." },
      { title: "Guest selection", description: "Plan which virtual machines and containers are useful to monitor." },
      { title: "Focused monitoring", description: "Keep the setup purposeful and avoid collecting information without a clear use." },
      { title: "Automation ideas", description: "Explore ways integration data can support Home Assistant automations." },
      { title: "Everyday use", description: "Organize the information that matters most to your environment." },
    ],
  },
  {
    slug: "pdm",
    title: "PDM",
    href: "/docs/pdm/",
    icon: "server",
    summary: "Centralized monitoring for Proxmox Datacenter Manager and its PVE/PBS remotes.",
    introduction: "A focused guide to connecting Proxmox Datacenter Manager and understanding its centralized status, capacity, inventory, remotes and update information.",
    topics: [
      { title: "Overview", description: "Understand the purpose and current scope of PDM monitoring." },
      { title: "Configuration", description: "Add a PDM connection to Home Assistant." },
      { title: "Authentication", description: "Prepare the API token used by the PDM connection." },
      { title: "Datacenter Monitoring", description: "Read centralized status, inventory and capacity." },
      { title: "Remotes", description: "Understand the PVE/PBS remotes managed by PDM." },
      { title: "Updates", description: "Interpret available updates and snapshot freshness." },
      { title: "Troubleshooting", description: "Diagnose connection, permission and data-availability issues." },
    ],
  },
  {
    slug: "pve",
    title: "PVE",
    href: "/docs/pve/",
    icon: "server",
    summary: "Guidance for configuring, monitoring and managing your Proxmox VE nodes.",
    introduction: "A focused map for configuring and understanding PVE-related monitoring.",
    topics: [
      { title: "Overview", description: "Understand how PVE monitoring fits into Home Assistant." },
      { title: "Configuration", description: "Connect a PVE server and choose what to monitor." },
      { title: "Authentication", description: "Prepare a dedicated account and API token." },
      { title: "Node monitoring", description: "Read node status, resources and network activity." },
      { title: "VM & CT monitoring", description: "Monitor selected guests and supported controls." },
      { title: "Hardware", description: "Understand host temperatures, drives and memory data." },
      { title: "Storage", description: "Monitor PVE storage and mounted disks." },
      { title: "Troubleshooting", description: "Diagnose connection, permission and missing-data issues." },
    ],
  },
  {
    slug: "pbs",
    title: "PBS",
    href: "/docs/pbs/",
    icon: "backup",
    summary: "Monitoring, backup management and automation guidance for Proxmox Backup Server.",
    introduction: "A documentation map covering PBS monitoring as well as action-oriented Home Assistant use cases.",
    topics: [
      { title: "Overview", description: "Understand PBS monitoring and how it differs from PVE." },
      { title: "Configuration", description: "Connect a Proxmox Backup Server to Home Assistant." },
      { title: "Authentication", description: "Prepare a dedicated PBS account and API Token." },
      { title: "Datastores", description: "Monitor capacity, usage and deduplication." },
      { title: "Backups", description: "Read stored-backup summaries and latest-backup information." },
      { title: "Maintenance", description: "Understand status and supported PBS operations." },
      { title: "Tasks", description: "Interpret recent PBS tasks and their results." },
      { title: "Troubleshooting", description: "Diagnose connection, permission and data-availability issues." },
    ],
  },
  {
    slug: "cluster",
    title: "Cluster",
    href: "/docs/cluster/",
    icon: "cluster",
    summary: "Cluster-wide monitoring, resources, health and operational guidance.",
    introduction: "A structured entry point for information that belongs to the cluster rather than a single node.",
    topics: [
      { title: "Overview", description: "Understand the cluster-wide view and how it complements PVE." },
      { title: "Quorum & Nodes", description: "Read cluster status, quorum and node availability." },
      { title: "Resources", description: "Interpret aggregated CPU, memory and storage usage." },
      { title: "Guests", description: "Understand cluster-wide VM and container summaries." },
      { title: "High Availability", description: "Monitor the HA environment when it is configured." },
      { title: "Tasks & Diagnostics", description: "Investigate failed tasks, replication and firewall state." },
      { title: "Backup Health", description: "Read PVE-side backup jobs, age and health together." },
      { title: "Troubleshooting", description: "Diagnose quorum, resource, task and backup issues." },
    ],
  },
  {
    slug: "dashboard",
    title: "Dashboard",
    href: "/docs/dashboard/",
    icon: "dashboard",
    summary: "Installation, configuration and usage guidance for the Proxmox Extended Sensors dashboard.",
    introduction: "Install and use the automatically generated dashboard, understand how it adapts to your environment, and choose the right customization approach.",
    topics: [
      { title: "Overview", description: "Understand the dashboard philosophy, information hierarchy and operating modes." },
      { title: "Installation", description: "Install the required resource and create the Proxmox Extended Sensors community dashboard." },
      { title: "Automatic Dashboard", description: "Learn how the dashboard adapts automatically to monitored resources and cluster changes." },
      { title: "Take Control", description: "Customize the dashboard through Home Assistant and understand which automatic behaviour is lost." },
      { title: "Customizing the Automatic Dashboard", description: "Modify the dashboard generator when automatic behaviour must be preserved." },
      { title: "Troubleshooting", description: "Diagnose installation, frontend, discovery and automatic-dashboard problems." },
    ],
  },
  {
    slug: "reference",
    title: "Reference",
    href: "/docs/reference/",
    icon: "docs",
    summary: "Technical reference for sensors, entities, devices and supported actions.",
    introduction: "A technical dictionary of the entities exposed by Proxmox Extended Sensors. Search by entity name, resource or capability, or browse the categories below.",
    topics: [
      { title: "PVE Node Sensors", description: "Node state, resources, health and actions." },
      { title: "Hardware & Memory", description: "Detected temperatures, fans, voltages and DIMMs." },
      { title: "VM & CT", description: "Monitored guests and their controls." },
      { title: "Storage, Disks & ZFS", description: "Storage resources, disks, mounts and pools." },
      { title: "PBS Server & Datastores", description: "Backup server and datastore information." },
      { title: "PBS Maintenance & Actions", description: "Tasks, maintenance state and controls." },
      { title: "Cluster Sensors", description: "Quorum, resources and cluster health." },
      { title: "Backup & Replication", description: "Backup health and replication state." },
      { title: "Entities, Devices & Availability", description: "Identity and conditional availability." },
      { title: "Troubleshooting", description: "Locating and interpreting entities." },
    ],
  },
];

export const documentationLanguages = [
  { code: "de", label: "Deutsch" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "it", label: "Italiano" },
  { code: "nl", label: "Nederlands" },
  { code: "pt", label: "Português" },
  { code: "ru", label: "Русский" },
  { code: "uk", label: "Українська" },
  { code: "zh", label: "中文" },
];

export const getDocumentationCategory = (slug: string) => {
  const category = documentationCategories.find((item) => item.slug === slug);
  if (!category) throw new Error(`Unknown documentation category: ${slug}`);
  return category;
};
