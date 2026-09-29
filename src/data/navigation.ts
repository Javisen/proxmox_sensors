export type NavigationIcon =
  | "home"
  | "server"
  | "backup"
  | "cluster"
  | "dashboard"
  | "docs"
  | "install"
  | "github";

export interface NavigationItem {
  label: string;
  href: string;
  icon: NavigationIcon;
  external?: boolean;
}

export const navigationItems: NavigationItem[] = [
  { label: "Home", href: "/", icon: "home" },
  { label: "PVE", href: "/pve/", icon: "server" },
  { label: "PBS", href: "/pbs/", icon: "backup" },
  { label: "Cluster", href: "/cluster/", icon: "cluster" },
  { label: "Dashboard", href: "/dashboard/", icon: "dashboard" },
  { label: "Documentation", href: "/docs/", icon: "docs" },
  { label: "Installation", href: "/installation/", icon: "install" },
  {
    label: "GitHub",
    href: "https://github.com/Javisen/proxmox_sensors",
    icon: "github",
    external: true,
  },
];
