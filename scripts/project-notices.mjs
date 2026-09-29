export const NOTICE_LEVELS = Object.freeze(["info", "warning", "critical", "success"]);

const NOTICE_FIELDS = new Set([
  "id",
  "active",
  "level",
  "title",
  "message",
  "link",
  "linkLabel",
  "startsAt",
  "expiresAt",
]);

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${field} must be a non-empty string`);
  }

  return value.trim();
}

function optionalString(value, field) {
  if (value === undefined || value === null) return null;
  return requiredString(value, field);
}

function isoDate(value, field) {
  if (value === undefined || value === null) return null;

  const normalized = requiredString(value, field);
  const match = normalized.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,9})?)?(Z|[+-]\d{2}:\d{2}))?$/,
  );

  if (!match) {
    throw new Error(`${field} must be a valid ISO-8601 date with a timezone when time is included`);
  }

  const [, year, month, day, hour = "00", minute = "00", second = "00", zone] = match;
  const calendarCheck = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  const validCalendarDate = calendarCheck.getUTCFullYear() === Number(year)
    && calendarCheck.getUTCMonth() === Number(month) - 1
    && calendarCheck.getUTCDate() === Number(day);

  if (!validCalendarDate || Number(hour) > 23 || Number(minute) > 59 || Number(second) > 59) {
    throw new Error(`${field} must be a valid ISO-8601 date`);
  }

  if (zone && zone !== "Z") {
    const [offsetHour, offsetMinute] = zone.slice(1).split(":").map(Number);
    if (offsetHour > 23 || offsetMinute > 59) {
      throw new Error(`${field} must contain a valid timezone offset`);
    }
  }

  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${field} must be a valid ISO-8601 date`);
  }

  return parsed.toISOString();
}

function normalizeLink(value, noticeId, warnings) {
  if (value === undefined || value === null) return null;

  try {
    const url = new URL(requiredString(value, `notice ${noticeId}.link`));
    if (url.protocol !== "https:") throw new Error("unsupported protocol");
    return url.href;
  } catch {
    warnings.push(`Notice "${noticeId}": link omitted because it is not a valid HTTPS URL.`);
    return null;
  }
}

function normalizeNotice(value, index, warnings) {
  if (!isObject(value)) {
    throw new Error(`notices[${index}] must be an object`);
  }

  const unknownFields = Object.keys(value).filter((field) => !NOTICE_FIELDS.has(field));
  if (unknownFields.length > 0) {
    throw new Error(`notices[${index}] contains unsupported fields: ${unknownFields.join(", ")}`);
  }

  const id = requiredString(value.id, `notices[${index}].id`);
  if (typeof value.active !== "boolean") {
    throw new Error(`notice "${id}".active must be a boolean`);
  }
  if (!NOTICE_LEVELS.includes(value.level)) {
    throw new Error(`notice "${id}".level must be one of: ${NOTICE_LEVELS.join(", ")}`);
  }

  const startsAt = isoDate(value.startsAt, `notice "${id}".startsAt`);
  const expiresAt = isoDate(value.expiresAt, `notice "${id}".expiresAt`);
  if (startsAt && expiresAt && Date.parse(startsAt) >= Date.parse(expiresAt)) {
    throw new Error(`notice "${id}" must expire after it starts`);
  }

  const link = normalizeLink(value.link, id, warnings);
  const suppliedLinkLabel = optionalString(value.linkLabel, `notice "${id}".linkLabel`);
  if (!link && suppliedLinkLabel) {
    warnings.push(`Notice "${id}": linkLabel omitted because no valid link is available.`);
  }

  return {
    id,
    active: value.active,
    level: value.level,
    title: requiredString(value.title, `notice "${id}".title`),
    message: requiredString(value.message, `notice "${id}".message`),
    link,
    linkLabel: link ? (suppliedLinkLabel ?? "More information") : null,
    startsAt,
    expiresAt,
  };
}

export function isNoticeVisible(notice, now = new Date()) {
  const timestamp = now instanceof Date ? now.getTime() : new Date(now).getTime();
  if (Number.isNaN(timestamp)) throw new Error("Notice visibility requires a valid current date");

  return notice.active === true
    && (notice.startsAt === null || Date.parse(notice.startsAt) <= timestamp)
    && (notice.expiresAt === null || timestamp < Date.parse(notice.expiresAt));
}

export function visibleNoticeIds(notices, now = new Date()) {
  return notices.filter((notice) => isNoticeVisible(notice, now)).map((notice) => notice.id);
}

export function normalizeNoticesDocument(document, { now = new Date() } = {}) {
  if (!isObject(document)) {
    throw new Error("Notices document must be an object");
  }

  const topLevelFields = Object.keys(document);
  if (topLevelFields.length !== 1 || topLevelFields[0] !== "notices") {
    throw new Error("Notices document must contain only the notices field");
  }
  if (!Array.isArray(document.notices)) {
    throw new Error("Notices document notices field must be an array");
  }

  const warnings = [];
  const notices = document.notices.map((notice, index) => normalizeNotice(notice, index, warnings));
  const ids = new Set();

  for (const notice of notices) {
    if (ids.has(notice.id)) {
      throw new Error(`Notice id "${notice.id}" is duplicated`);
    }
    ids.add(notice.id);
  }

  return {
    notices,
    visibleNoticeIds: visibleNoticeIds(notices, now),
    warnings,
  };
}
