const normalize = (value) => value
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLocaleLowerCase()
  .replace(/[^a-z0-9_]+/g, " ")
  .trim();

export const referenceSlug = (value) => normalize(value).replace(/[ _]+/g, "-");

export const referenceEntryId = (module, sectionId, groupTitle, entryName) =>
  `reference-${referenceSlug(module)}-${referenceSlug(sectionId)}-${referenceSlug(groupTitle)}-${referenceSlug(entryName)}`;

export const buildReferenceSearchIndex = (sources) => sources.flatMap((source) =>
  source.groups.flatMap((group) => group.entries.map((entry) => {
    const identifier = referenceSlug(entry.name).replace(/-/g, "_");
    const attributes = [...(entry.attributes ?? []), ...(entry.moreAttributes ?? [])];
    return {
      id: referenceEntryId(source.module, source.sectionId, group.title, entry.name),
      href: `#${referenceEntryId(source.module, source.sectionId, group.title, entry.name)}`,
      module: source.module,
      group: group.title,
      name: entry.name,
      identifier,
      type: entry.type,
      attributes,
      searchText: normalize([
        entry.name,
        identifier,
        entry.type,
        entry.description,
        entry.state,
        entry.condition,
        group.title,
        ...attributes,
      ].filter(Boolean).join(" ")),
    };
  })),
);

const stripMarkdown = (value) => value
  .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
  .replace(/[*_#>`-]/g, " ")
  .replace(/\s+/g, " ")
  .trim();

export const extractPdmReferenceEntries = (documents) => {
  const boldNames = documents.flatMap((document) => [
    ...document.source.matchAll(/\*\*([^*\n]+)\*\*/g),
  ].map((match) => match[1].trim()));
  const occurrences = boldNames.reduce((counts, name) => {
    counts.set(name, (counts.get(name) ?? 0) + 1);
    return counts;
  }, new Map());

  return [...occurrences.entries()]
    .filter(([, count]) => count > 1)
    .map(([name]) => {
      const candidates = documents
        .filter((document) => document.source.includes(`**${name}**`))
        .map((document) => {
          const headingPattern = new RegExp(`^###\\s+${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*$`, "m");
          const headingMatch = headingPattern.exec(document.source);
          const start = headingMatch?.index ?? document.source.indexOf(`**${name}**`);
          const remainder = document.source.slice(start);
          const nextHeading = remainder.slice(1).search(/^###\s+/m);
          const section = nextHeading >= 0 ? remainder.slice(0, nextHeading + 1) : remainder;
          return { document, section, hasHeading: Boolean(headingMatch) };
        })
        .sort((left, right) => Number(right.hasHeading) - Number(left.hasHeading) || right.section.length - left.section.length);
      const best = candidates[0];
      const technicalTerms = [...best.section.matchAll(/`([^`\n]+)`/g)].map((match) => match[1]);
      const href = best.hasHeading
        ? `${best.document.href.split("#")[0]}#${referenceSlug(name)}`
        : best.document.href;
      const description = stripMarkdown(best.section);
      const identifier = referenceSlug(name).replace(/-/g, "_");

      return {
        id: `pdm-${referenceSlug(name)}`,
        href,
        module: "PDM",
        group: best.document.group,
        name,
        identifier,
        type: "Sensor",
        attributes: [],
        searchText: normalize([name, identifier, best.document.group, description, ...technicalTerms].join(" ")),
      };
    })
    .sort((left, right) => left.name.localeCompare(right.name));
};

export const normalizeReferenceSearch = normalize;
