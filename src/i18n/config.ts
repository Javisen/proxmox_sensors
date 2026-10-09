export const supportedLocales = ["en", "es"] as const;

export type Locale = (typeof supportedLocales)[number];

export const defaultLocale: Locale = "en";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  es: "Español",
};

export const isLocale = (value: string | undefined): value is Locale =>
  supportedLocales.includes(value as Locale);

const relativeToBase = (pathname: string, baseUrl = "/"): string => {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return normalizedPath.startsWith(normalizedBase)
    ? normalizedPath.slice(normalizedBase.length)
    : normalizedPath.replace(/^\//, "");
};

export const localeFromPath = (pathname: string, baseUrl = "/"): Locale => {
  const segment = relativeToBase(pathname, baseUrl).split("/").filter(Boolean)[0];
  return isLocale(segment) ? segment : defaultLocale;
};

export const stripLocaleFromPath = (pathname: string, baseUrl = "/"): string => {
  const relative = relativeToBase(pathname, baseUrl);
  const [firstSegment, ...remainingSegments] = relative.split("/");
  const stripped = isLocale(firstSegment) ? remainingSegments.join("/") : relative;
  return `/${stripped}`.replace(/\/{2,}/g, "/");
};

export const localizePath = (pathname: string, locale: Locale, baseUrl = "/"): string => {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const relativePath = stripLocaleFromPath(pathname, normalizedBase).replace(/^\//, "");

  if (locale === defaultLocale) {
    return relativePath === "" ? normalizedBase : `${normalizedBase}${relativePath}`;
  }

  return relativePath === ""
    ? `${normalizedBase}${locale}/`
    : `${normalizedBase}${locale}/${relativePath}`;
};
