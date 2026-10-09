import type { Locale } from "./config";

const english = {
  "shell.skip": "Skip to content",
  "shell.openNavigation": "Open navigation",
  "shell.primaryNavigation": "Primary navigation",
  "shell.closeNavigation": "Close navigation",
  "shell.language": "Language",
  "shell.changeLanguage": "Change language",
  "shell.currentLanguage": "Current language",
  "shell.opensNewTab": "opens in a new tab",
  "nav.home": "Home",
  "nav.documentation": "Documentation",
  "nav.development": "Development",
  "nav.installation": "Installation",
  "nav.cluster": "Cluster",
} as const;

export type UiKey = keyof typeof english;

const spanish: Record<UiKey, string> = {
  "shell.skip": "Saltar al contenido",
  "shell.openNavigation": "Abrir navegación",
  "shell.primaryNavigation": "Navegación principal",
  "shell.closeNavigation": "Cerrar navegación",
  "shell.language": "Idioma",
  "shell.changeLanguage": "Cambiar idioma",
  "shell.currentLanguage": "Idioma actual",
  "shell.opensNewTab": "se abre en una pestaña nueva",
  "nav.home": "Inicio",
  "nav.documentation": "Documentación",
  "nav.development": "Desarrollo",
  "nav.installation": "Instalación",
  "nav.cluster": "Clúster",
};

const catalogs: Record<Locale, Record<UiKey, string>> = {
  en: english,
  es: spanish,
};

export const ui = (locale: Locale, key: UiKey): string => catalogs[locale][key];
