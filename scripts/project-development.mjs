export const DEVELOPMENT_STATUSES = Object.freeze([
  "idea",
  "study",
  "planned",
  "development",
  "testing",
  "completed",
  "paused",
]);

export const RELEASE_STATUSES = Object.freeze([
  "planning",
  "development",
  "testing",
  "completed",
  "paused",
]);

const DOCUMENT_FIELDS = new Set(["version", "release_status", "items"]);
const ITEM_FIELDS = new Set(["id", "active", "status", "progress", "title", "message"]);

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${field} must be a non-empty string`);
  }

  return value.trim();
}

function unsupportedFields(value, allowedFields, field) {
  const fields = Object.keys(value).filter((key) => !allowedFields.has(key));
  if (fields.length > 0) {
    throw new Error(`${field} contains unsupported fields: ${fields.join(", ")}`);
  }
}

function normalizeProgress(value, itemId) {
  if (value === null) return null;
  if (!Number.isInteger(value) || value < 0 || value > 100) {
    throw new Error(`development item "${itemId}".progress must be null or an integer from 0 to 100`);
  }

  return value;
}

function normalizeItem(value, index) {
  if (!isObject(value)) {
    throw new Error(`development.items[${index}] must be an object`);
  }

  unsupportedFields(value, ITEM_FIELDS, `development.items[${index}]`);
  const id = requiredString(value.id, `development.items[${index}].id`);

  if (typeof value.active !== "boolean") {
    throw new Error(`development item "${id}".active must be a boolean`);
  }
  if (!DEVELOPMENT_STATUSES.includes(value.status)) {
    throw new Error(
      `development item "${id}".status must be one of: ${DEVELOPMENT_STATUSES.join(", ")}`,
    );
  }

  return {
    id,
    active: value.active,
    status: value.status,
    progress: normalizeProgress(value.progress, id),
    title: requiredString(value.title, `development item "${id}".title`),
    message: requiredString(value.message, `development item "${id}".message`),
  };
}

export function normalizeDevelopmentDocument(document) {
  if (!isObject(document)) {
    throw new Error("Development document must be an object");
  }

  unsupportedFields(document, DOCUMENT_FIELDS, "Development document");
  const version = requiredString(document.version, "development.version");
  const releaseStatus = requiredString(document.release_status, "development.release_status");

  if (!RELEASE_STATUSES.includes(releaseStatus)) {
    throw new Error(`development.release_status must be one of: ${RELEASE_STATUSES.join(", ")}`);
  }
  if (!Array.isArray(document.items)) {
    throw new Error("development.items must be an array");
  }

  const items = document.items.map(normalizeItem);
  const ids = new Set();
  for (const item of items) {
    if (ids.has(item.id)) {
      throw new Error(`Development item id must be unique: "${item.id}"`);
    }
    ids.add(item.id);
  }

  return { version, releaseStatus, items };
}
