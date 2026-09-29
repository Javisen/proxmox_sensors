/** Generated dashboard only: selection and resource identities belong to Python. */
const TYPE = "proxmox-sensors";
const FAMILIES = ["pve", "pbs", "cluster"];
const TITLES = {pve: "PVE", pbs: "PBS", cluster: "Cluster"};
const ICONS = {pve: "mdi:server", pbs: "mdi:backup-restore", cluster: "mdi:server-network"};
const HEALTH_TILES = new Set(["cpu", "memory", "swap", "rootfs", "load", "iowait", "ksm", "score",
  "cpu_usage", "ram_usage", "ram_total", "ram_used", "ram_free", "temperature"]);
// `background` is a native Lovelace view property. HA's hui-root applies it to
// hui-view-background for the active view, so it cannot leak to app chrome or
// unrelated dashboards. Card Mod remains responsible for card-level styling.
const DASHBOARD_BACKGROUND = "#0b1216";

function options(config) {
  const selected = config.dashboards;
  if (selected !== undefined && (!Array.isArray(selected) || selected.some(x => !FAMILIES.includes(x)))) {
    throw new Error("dashboards must be an array containing pve, pbs or cluster");
  }
  for (const key of ["show_diagnostics", "show_maintenance_controls"]) {
    if (config[key] !== undefined && typeof config[key] !== "boolean") throw new Error(`${key} must be boolean`);
  }
  return {dashboards: selected ?? FAMILIES, show_diagnostics: config.show_diagnostics ?? true,
    show_maintenance_controls: config.show_maintenance_controls ?? true};
}

function label(ref) {
  const text = ref.metric.replaceAll("_", " ");
  return (ref.job_id ? `${ref.job_id} · ` : "") + text.charAt(0).toUpperCase() + text.slice(1);
}

function styled(card, layout, variant = "normal_card") {
  const css = layout.style?.[variant]?.css;
  return css ? {...card, card_mod: {style: css}} : card;
}

function darkView(view) {
  return {...view, background: DASHBOARD_BACKGROUND};
}

function resourceCards(resource, block, layout, opts) {
  const refs = resource.references.filter(ref => opts.show_maintenance_controls || !ref.entity_id.startsWith("button."));
  if (!refs.length) return [];
  const cards = [];
  const rows = [];
  for (const ref of refs) {
    // Domain denotes an existing HA button, never its localized name or action.
    if (ref.entity_id.startsWith("button.")) {
      cards.push(styled({type: "tile", entity: ref.entity_id, name: `${resource.title} · ${label(ref)}`,
        tap_action: {action: "perform-action", perform_action: "button.press",
          target: {entity_id: ref.entity_id}, confirmation: {text: `Run ${label(ref)} on ${resource.title}?`}},
        icon_tap_action: {action: "none"}, hold_action: {action: "none"}, double_tap_action: {action: "none"}}, layout));
    } else if (!ref.attribute && HEALTH_TILES.has(ref.metric)
        && ["node_health", "server_health", "cluster_health", "temperatures"].includes(block.id)) {
      cards.push(styled({type: "tile", entity: ref.entity_id,
        name: block.id === "temperatures" ? resource.title : label(ref),
        tap_action: {action: "more-info"}, icon_tap_action: {action: "more-info"}}, layout));
    } else {
      rows.push(ref.attribute ? {type: "attribute", entity: ref.entity_id, attribute: ref.attribute, name: label(ref)}
        : {entity: ref.entity_id, name: label(ref)});
    }
  }
  if (rows.length) cards.unshift(styled({type: "entities", title: resource.title, entities: rows,
    show_header_toggle: false}, layout, block.style));
  return cards;
}

// Escape each non-lowercase-alphanumeric code point (including separators).
// Unlike slugification, this preserves distinctions such as A/a and a-b/a b.
function encodePathPart(part) {
  return Array.from(part, char => /^[a-z0-9]$/.test(char)
    ? char : `_${char.codePointAt(0).toString(16)}_`).join("");
}

export function nodeViewPath(group) {
  if (typeof group.entry_id !== "string" || !group.entry_id) throw new Error("Missing PVE entry identity");
  return `pve-node-${encodePathPart(group.entry_id)}`;
}

export function resourceSubviewPath(resource) {
  const parts = JSON.parse(resource.resource_id);
  if (!Array.isArray(parts) || !parts.length || parts.some(part => typeof part !== "string")) {
    throw new Error("Invalid logical resource identity for PVE subview");
  }
  const guest = ["vm", "ct"].includes(resource.kind);
  return `pve-${guest ? "guest" : "storage"}-` + parts.map(encodePathPart).join("-");
}

// HA dashboard panels have their own url_path. Resolve from the active route,
// including direct subview loads; never assume a fixed /lovelace base.
export function dashboardBasePath(pathname, panels = {}) {
  const matches = Object.values(panels).filter(panel => panel.component_name === "lovelace"
    && panel.url_path && (pathname === `/${panel.url_path}` || pathname.startsWith(`/${panel.url_path}/`)));
  matches.sort((a, b) => b.url_path.length - a.url_path.length);
  return matches.length ? `/${matches[0].url_path}` : null;
}

function resourceTitle(resource) {
  return ["vm", "ct"].includes(resource.kind)
    ? `${resource.kind === "vm" ? "VM" : "CT"} ${resource.guest_id} · ${resource.title}` : resource.title;
}

// PVE main presentation is independent of the generic family/subview renderer.
// HA Markdown strips class, style and data-* attributes. All presentation
// selectors below use admitted HTML structure, a/abbr title, and font color.
// Dynamic CSS belongs to Card Mod's template, never inline Markdown styles.
const PVE_CSS = `ha-card { background: #10191e; color: #fff; border: 1px solid #303b42;
  border-top: 4px solid #ef7d00; border-radius: 15px; box-shadow: none;
  --primary-text-color: #fff; --secondary-text-color: #b7c2cc; }
  ha-markdown { padding: 0 !important; }`;
const PVE_MARKDOWN_CSS = `:host { padding: 0 !important; }
  * { box-sizing: border-box; }
  section { padding: 14px; min-height: 240px; }
  section > header { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
  h2 { font: inherit; font-weight: 600; margin: 0; color: #fff; }
  ha-icon { --mdc-icon-size: 24px; flex: none; }
  section > header > ha-icon:first-child, header > div > ha-icon { color: #ef7d00; }
  ha-icon[icon="mdi:chevron-right"] { margin-left: auto; color: #b7c2cc; --mdc-icon-size: 18px; }
  dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 10px; margin: 0; }
  dl > div { border: 1px solid #303b42; border-radius: 7px; background: #151f25;
    display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 14px 6px; min-width: 0; }
  dt { color: #cbd5df; text-align: center; overflow-wrap: anywhere; }
  dd { margin: 0; width: 100%; display: flex; flex-direction: column; align-items: center; gap: 14px; }
  dd strong { font-weight: 600; color: #fff; font-variant-numeric: tabular-nums; }
  dd > ha-icon { color: #ef7d00; --mdc-icon-size: 30px; }
  figure { display: grid; place-items: center; width: 100%; max-width: 88px; aspect-ratio: 1; position: relative; margin: 0; }
  figure::before { content: ''; position: absolute; inset: 0; border-radius: 50%;
    background: conic-gradient(from 225deg, #4cc653 0deg var(--fill, 0deg), #303b42 var(--fill, 0deg) 270deg, transparent 270deg);
    mask: radial-gradient(farthest-side, transparent calc(100% - 6px), #000 0); }
  figure strong { text-align: center; overflow-wrap: anywhere; }
  nav { display: flex; flex-direction: column; gap: 5px; }
  nav > :is(a, article) { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center;
    gap: 10px; min-height: 42px; padding: 8px; border: 1px solid #2c373e; border-radius: 8px;
    color: #dbe3eb; background: #101a20; text-decoration: none; }
  nav > a:hover { background: #1b2931; border-color: #697b88; }
  nav > a:focus-visible { outline: 2px solid #ef7d00; outline-offset: 2px; }
  nav > :is(a, article) > ha-icon { color: #ef7d00; --mdc-icon-size: 18px; }
  nav span { min-width: 0; overflow-wrap: anywhere; }
  nav > article > span:last-child { text-align: right; font-variant-numeric: tabular-nums; }
  a[title="Storage"] { grid-template-columns: 20px minmax(65px, 1fr) minmax(50px, 1fr) auto 16px; }
  a[title="Storage"] > u { background: #243037; border-radius: 8px; height: 12px; overflow: hidden; text-decoration: none; }
  a[title="Storage"] > u::before { content: ''; display: block; height: 100%; width: var(--usage, 0%); background: #4193ef; border-radius: inherit; }
  a[title="Guest"] { grid-template-columns: 14px auto minmax(0, 1fr) auto 16px; }
  a[title="Guest"] > span:last-of-type { display: flex; gap: 6px; white-space: nowrap; font-variant-numeric: tabular-nums; }
  nav > :is(a[title="Replication"], article:has(> abbr)) { grid-template-columns: 14px minmax(0, 1fr) auto 16px; }
  abbr { text-decoration: none; border: 0; }
  font > i { width: 12px; height: 12px; border-radius: 50%; background: currentColor; display: inline-block; }
  mark { display: inline-flex; align-items: center; border-radius: 9px; padding: 10px 14px; background: #253038; }
  mark > font { display: inline-flex; align-items: center; gap: 8px; }
  mark:has(font[color="#4cc653"]) { background: #132d23; border: 1px solid #29513a; }
  mark:has(font[color="#ef5350"]) { background: #351b20; border: 1px solid #66333b; }
  ha-markdown-element > header { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; min-height: 92px; padding: 16px 20px; }
  ha-markdown-element > header > div { display: flex; align-items: center; gap: 14px; min-width: 0; }
  header > div > strong { font-weight: 600; color: #fff; }
  aside { margin-left: auto; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
  aside > div { display: flex; flex-direction: column; gap: 6px; border-left: 1px solid #28343b; padding-left: 16px; }
  aside > div > span { color: #b7c2cc; }
  header img { width: 56px; height: auto; object-fit: contain; }
  @media (max-width: 600px) { section { min-height: 0; } aside { margin-left: 0; gap: 12px; }
    a[title="Guest"], a[title="Storage"] { gap: 6px; } }`;

const blockRefs = (group, block) => (group.blocks[block] || []).flatMap(resource =>
  resource.references.map(ref => ({resource, ref})));
const metricRef = (resource, metric) => resource.references.find(ref => ref.metric === metric);
const expression = ref => ref.attribute
  ? `state_attr(${JSON.stringify(ref.entity_id)}, ${JSON.stringify(ref.attribute)})`
  : `states(${JSON.stringify(ref.entity_id)})`;
const value = ref => `{{ (${expression(ref)} if ${expression(ref)} is not none else '—') | e }}`;
const percent = ref => `{% set n = ${expression(ref)} %}{% if is_number(n) %}{{ n | float | round(1) }} %{% else %}{{ (n if n is not none else '—') | e }}{% endif %}`;
// Model text is a Jinja string literal and escaped HTML, not executable markup.
const text = input => `{{ ${JSON.stringify(String(input))} | e }}`;
const icon = name => `<ha-icon icon="${name}"></ha-icon>`;
const chevron = icon('mdi:chevron-right');
const semanticState = ref => `{% set raw = ${ref ? expression(ref) : 'none'} %}{% set s = (raw if raw is not none else '—') | string %}{% set color = '#4cc653' if s | lower in ['online','running','ok','healthy'] else '#ffca28' if s | lower in ['warning','degraded'] else '#ef5350' if s | lower in ['error','critical','offline','faulted','failed'] else '#a6b0b9' %}`;
const statusDot = '<abbr title="{{ s | e }}"><font color="{{ color }}"><i></i></font></abbr>';
function statusValue(ref, pill = false) {
  const body = `<font color="{{ color }}">${pill ? '<i></i> ' : ''}{{ s | e }}</font>`;
  return `${semanticState(ref)}${pill ? `<mark>${body}</mark>` : body}`;
}
// Standard state display metadata only; no hardware attribute discovery.
const withUnit = ref => `${value(ref)}{% if is_number(${expression(ref)}) %} {{ (state_attr(${JSON.stringify(ref.entity_id)}, 'unit_of_measurement') or '') | e }}{% endif %}`;
function pveMarkdown(title, content, refs = [], headingIcon = 'mdi:information-outline', dynamicCSS = '') {
  const heading = title ? `<header>${icon(headingIcon)}<h2>${title}</h2>${chevron}</header>` : '';
  return {type: 'markdown', content: title ? `<section>${heading}${content}</section>` : content,
    entity_id: [...new Set(refs.map(ref => ref.entity_id))], grid_options: {columns: 12, rows: 'auto'},
    card_mod: {style: {'.': title ? PVE_CSS : PVE_CSS.replace('border-top: 4px solid #ef7d00;', ''),
      'ha-markdown$': PVE_MARKDOWN_CSS + dynamicCSS}}};
}
function rowsCard(title, rows, refs, headingIcon, dynamicCSS = '') {
  return rows.length ? pveMarkdown(title, `<nav>${rows.join('')}</nav>`, refs, headingIcon, dynamicCSS) : null;
}
function readableTitle(resource, fallback) {
  const title = String(resource.title || '').trim();
  // Hide identifier-shaped labels; never interpret them as hardware categories.
  return !title || /(?:\b(?:sensor|binary_sensor)\.|\b(?:pve_|proxmox_|p_node_))/i.test(title) ? fallback : title;
}
function logicalName(resource, kind, fallback) {
  try {
    const parts = JSON.parse(resource.resource_id);
    if (parts.length === 3 && parts[1] === kind && typeof parts[2] === 'string') return parts[2];
  } catch { /* Optional display name; navigation validates its own identity. */ }
  return readableTitle(resource, fallback);
}
function guestName(resource) {
  const title = readableTitle(resource, '—');
  const type = resource.kind === 'ct' ? 'CT' : 'VM';
  // Exact wrappers emitted by sensor/ct.py and sensor/vm.py, display only.
  const prefix = resource.kind === 'ct' ? '3. CT: ' : '4. VM: ';
  const suffix = `-(${resource.guest_id})`;
  if (title.startsWith(prefix) && title.endsWith(suffix)) return title.slice(prefix.length, -suffix.length);
  return title.startsWith(`${type}: `) ? title.slice(type.length + 2) : title;
}
function pveVersion(ref) {
  return `{% set v = ${expression(ref)} %}{{ (v.split('/')[1] if v is string and v.startswith('pve-manager/') else (v if v is not none else '—')) | e }}`;
}
const PVE_CLUSTER_HEADER_CSS = `ha-markdown-element > header > div:nth-of-type(2) { margin-left: auto; min-width: 110px;
  flex-direction: column; align-items: center; gap: 6px; }
  ha-markdown-element > header > div:nth-of-type(2) > span { color: #b7c2cc; }
  ha-markdown-element > header > aside { margin-left: 0; }
  @media (max-width: 600px) { ha-markdown-element > header > div:nth-of-type(2) { margin-left: 0; align-items: flex-start; } }`;
function buildPveNodeHeader(group) {
  const refs = [...blockRefs(group, 'header'), ...blockRefs(group, 'node_health')].map(item => item.ref);
  const facts = [], selected = [];
  const nodeRef = refs.find(ref => ref.metric === 'health' && !ref.attribute);
  const cluster = nodeRef
    ? `{% set cluster_status = state_attr(${JSON.stringify(nodeRef.entity_id)}, 'cluster_association_status') %}{% set cluster_name = state_attr(${JSON.stringify(nodeRef.entity_id)}, 'associated_cluster_name') %}{% set cluster_labels = {'independent':'Independent','legacy':'Legacy','pending':'Pending','invalid':'Invalid','incomplete':'Incomplete','cluster_inactive':'Inactive','ambiguous':'Ambiguous'} %}{{ (cluster_name if cluster_status == 'associated' and cluster_name else cluster_labels.get(cluster_status, '—')) | e }}`
    : '—';
  for (const [metric, title] of [['uptime_seconds', 'Uptime'], ['kernel_version', 'Kernel'], ['pve_version', 'PVE'], ['health', 'Health'], ['status', 'Status']]) {
    const ref = (metric === 'kernel_version' && refs.find(item => item.metric === metric && !item.attribute))
      || refs.find(item => item.metric === metric);
    if (!ref) continue;
    selected.push(ref);
    let display = value(ref);
    if (metric === 'uptime_seconds') display = `{% set u = ${expression(ref)} %}{% if is_number(u) and u | float >= 0 %}{{ (u | float / 86400) | int }}d {{ ((u | float % 86400) / 3600) | int }}h{% else %}{{ (u if u is not none else '—') | e }}{% endif %}`;
    if (metric === 'pve_version') display = pveVersion(ref);
    if (metric === 'status') display = statusValue(ref, true);
    facts.push(metric === 'status' ? display : `<div><span>${title}</span><strong>${display}</strong></div>`);
  }
  return {...pveMarkdown(null, `<header><div><img src="/proxmox_sensors/dashboard/logo_small.png" alt="Proxmox Extended Sensors" width="56">${icon('mdi:server')}<strong>${text(group.node || group.entry_id)} · Proxmox VE</strong></div><div><span>Cluster</span><strong>${cluster}</strong></div><aside>${facts.join('')}</aside></header>`, selected, 'mdi:information-outline', PVE_CLUSTER_HEADER_CSS),
    grid_options: {columns: 'full', rows: 'auto'}};
}
// Markdown admits anchors, but strips inline event handlers. Handle only our
// mini-panel links and dispatch HA's more-info event from the clicked element.
export function handlePveMoreInfo(event) {
  const link = event.composedPath().find(node => node?.getAttribute?.('title') === 'PVE more-info'
    && node.localName === 'a');
  const href = link?.getAttribute('href');
  if (!href?.startsWith('#proxmox-more-info=')) return;
  let entityId;
  try { entityId = decodeURIComponent(href.slice('#proxmox-more-info='.length)); } catch { return; }
  if (!/^(sensor|binary_sensor)\.[a-z0-9_]+$/.test(entityId)) return;
  event.preventDefault();
  event.stopPropagation();
  link.dispatchEvent(new CustomEvent('hass-more-info', {detail: {entityId}, bubbles: true, composed: true}));
}
const moreInfoListener = Symbol.for('proxmox-sensors.more-info-listener');
if (window.addEventListener && !window[moreInfoListener]) {
  window.addEventListener('click', handlePveMoreInfo, true);
  window[moreInfoListener] = handlePveMoreInfo;
}
const miniPanelLink = (ref, content = '') => `<a title="PVE more-info" href="#proxmox-more-info=${encodeURIComponent(ref.entity_id)}">${content}</a>`;
const MINI_PANEL_CSS = `dl > div { position: relative; }
  dl > div a[title="PVE more-info"] { position: absolute; inset: 0; z-index: 1; border-radius: 7px; cursor: pointer; }
  dl > div a[title="PVE more-info"]:hover { background: rgba(255,255,255,0.035); }
  dl > div a[title="PVE more-info"]:focus-visible { outline: 2px solid #b7c2cc; outline-offset: 2px; }`;
const PVE_TOP_CARD_CSS = `@media (min-width: 900px) { section { height: 360px; min-height: 360px; } }`;
const PVE_CENTERED_TOP_CARD_CSS = `@media (min-width: 900px) {
  section { display: flex; flex-direction: column; }
  section > dl { flex: 1; align-content: center; }
}`;
const PVE_GUEST_LIST_CSS = `@media (min-width: 900px) {
  section { height: 500px; min-height: 500px; display: flex; flex-direction: column; overflow: hidden; }
  section > header { flex: none; }
  section > nav { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden;
    padding-right: 4px; scrollbar-gutter: stable; overscroll-behavior: contain; }
}`;

function buildNodeHealthBlock(group) {
  const items = blockRefs(group, 'node_health'), selected = [], css = [];
  const panels = Object.entries({cpu: 'CPU', memory: 'RAM', swap: 'Swap', load: 'Load', ksm: 'KSM'}).flatMap(([metric, name]) => {
    const ref = items.find(item => item.ref.metric === metric)?.ref;
    if (!ref) return [];
    selected.push(ref);
    // Load has no denominator. Its neutral arc never pretends to be a percent.
    const status = items.find(item => item.ref.metric === 'ksm_status')?.ref;
    const fill = metric === 'load' ? '0' : metric === 'ksm' && status
      ? `{% set total = state_attr(${JSON.stringify(status.entity_id)}, 'ram_total_bytes') %}{{ ([0, [100 * (n | float) * 1073741824 / (total | float), 100] | min] | max) * 2.7 if is_number(n) and is_number(total) and total | float > 0 else 0 }}`
      : `{{ ([0, [100, n | float] | min] | max) * 2.7 if is_number(n) else 0 }}`;
    css.push(`{% set n = ${expression(ref)} %} dl > div:nth-child(${selected.length}) figure { --fill: ${fill}deg; }`);
    return [`<div><dt>${name}</dt><dd><figure><strong>${metric === 'ksm' ? withUnit(ref) : metric === 'load' ? value(ref) : percent(ref)}</strong></figure>${miniPanelLink(ref)}</dd></div>`];
  });
  return panels.length ? pveMarkdown('Node Health', `<dl>${panels.join('')}</dl>`, selected, 'mdi:pulse',
    MINI_PANEL_CSS + PVE_TOP_CARD_CSS + PVE_CENTERED_TOP_CARD_CSS
    + 'dl { grid-template-columns: repeat(5, minmax(0, 1fr)); } @media (max-width: 600px) { dl { grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); } }'
    + css.join('')) : null;
}
function buildTemperatureBlock(group) {
  const items = blockRefs(group, 'temperatures');
  return items.length ? pveMarkdown('Temperatures', `<dl>${items.map(({ref}) => {
    // Integration-owned translation keys identify the measured device, never
    // resource titles, localized names, entity IDs or enumeration order.
    const presentation = new Map([
      ['cpu_temperature', ['CPU', 'mdi:cpu-64-bit']],
      ['chipset_temp', ['Chipset', 'mdi:chip']],
      ['hw_nvme_temperature', ['NVMe', 'mdi:harddisk']],
    ]).get(ref.translation_key);
    const [name, deviceIcon] = presentation || [
      readableTitle({title: ref.name === ref.entity_id ? null : ref.name}, 'Temperature'), 'mdi:thermometer'];
    return `<div><dt>${text(name)}</dt><dd>${icon(deviceIcon)}<strong>${withUnit(ref)}</strong>${miniPanelLink(ref)}</dd></div>`;
  }).join('')}</dl>`, items.map(item => item.ref), 'mdi:thermometer',
    MINI_PANEL_CSS + PVE_TOP_CARD_CSS + PVE_CENTERED_TOP_CARD_CSS) : null;
}
function buildStorageSummaryBlock(group, basePath) {
  const resources = (group.blocks.storage || []).filter(resource => resource.references.length), refs = [], css = [];
  const rows = resources.map((resource, i) => {
    const usage = metricRef(resource, 'usage');
    if (usage) {
      refs.push(usage);
      css.push(`{% set n = ${expression(usage)} %} nav > a:nth-child(${i + 1}) > u { --usage: {{ [0, [100, n | float] | min] | max if is_number(n) else 0 }}%; }`);
    }
    return `<a title="Storage" href="${basePath}/${resourceSubviewPath(resource)}">${icon('mdi:database')}<span>${text(logicalName(resource, 'storage', 'Storage'))}</span>${usage ? '<u></u>' : '<span></span>'}<span>${usage ? percent(usage) : '—'}</span>${chevron}</a>`;
  });
  return rowsCard('Storage', rows, refs, 'mdi:database', css.join(''));
}
function buildGuestSummaryBlock(group, kind, basePath) {
  const resources = (group.blocks.guests || []).filter(resource => resource.kind === kind && resource.references.length), refs = [];
  const rows = resources.map(resource => {
    const status = metricRef(resource, 'status'), cpu = metricRef(resource, 'cpu_usage'), ram = metricRef(resource, 'memory_usage');
    const used = !ram && metricRef(resource, 'memory_used'), total = !ram && metricRef(resource, 'memory_total');
    refs.push(...[status, cpu, ram, ...(used && total ? [used, total] : [])].filter(Boolean));
    // Both current VM/CT memory sensors use GiB. Never display the operands or
    // turn absent/unavailable values into a percentage of zero.
    const memory = ram ? percent(ram) : used && total
      ? `{% set used = ${expression(used)} %}{% set total = ${expression(total)} %}{% if is_number(used) and is_number(total) and used | float >= 0 and total | float > 0 %}{{ (100 * (used | float) / (total | float)) | round(1) }} %{% else %}—{% endif %}` : '';
    const metrics = [cpu ? `<abbr title="CPU">${percent(cpu)}</abbr>` : '', memory ? `<abbr title="RAM">${memory}</abbr>` : ''].filter(Boolean).join('<span>|</span>');
    const running = `{% if s | lower == 'running' %}${metrics}{% else %}<font color="{{ color }}">{{ 'Stopped' if s | lower == 'stopped' else s | e }}</font>{% endif %}`;
    return `${semanticState(status)}<a title="Guest" href="${basePath}/${resourceSubviewPath(resource)}">${statusDot}<span>${text(resource.guest_id)}</span><span>${text(guestName(resource))}</span><span>${running}</span>${chevron}</a>`;
  });
  return rowsCard(`${kind === 'ct' ? 'CTs' : 'VMs'} (${resources.length})`, rows, refs,
    kind === 'ct' ? 'mdi:cube-outline' : 'mdi:monitor', PVE_GUEST_LIST_CSS);
}
function buildReplicationBlock(group, basePath) {
  const rows = [], refs = [];
  for (const resource of group.blocks.replication || []) {
    const status = metricRef(resource, 'replication_status');
    const jobs = [...new Set(resource.references.filter(ref => ref.job_id).map(ref => ref.job_id))];
    if (!jobs.length && status) jobs.push(null);
    for (const job of jobs) {
      if (status) refs.push(status);
      // A guest aggregate status is not an individual job result.
      const body = `${statusDot}<span>${text(resource.kind === 'ct' ? 'CT' : 'VM')} ${text(resource.guest_id)}${job ? ` · ${text(job)}` : ''}</span><abbr title="Guest replication status"><font color="{{ color }}">{{ s | e }}</font></abbr>${chevron}`;
      const guest = (group.blocks.guests || []).find(item => item.resource_id === resource.resource_id && item.references.length);
      rows.push(`${semanticState(status)}${guest ? `<a title="Replication" href="${basePath}/${resourceSubviewPath(guest)}">${body}</a>` : `<article>${body}</article>`}`);
    }
  }
  return rowsCard(`Replication (${rows.length})`, rows, refs, 'mdi:sync');
}
function buildNodeInfoBlock(group) {
  const rows = [], refs = [];
  const fields = [
    ['node_info', 'node_updates', 'Updates', 'mdi:update'],
    ['node_info', 'node_network_rx', 'Network RX', 'mdi:download-network'],
    ['node_info', 'node_network_tx', 'Network TX', 'mdi:upload-network'],
    ['node_health', 'iowait', 'I/O Wait', 'mdi:timer-sand'],
    ['node_info', 'ksm_status', 'KSM', 'mdi:memory'],
    ['tasks', 'node_last_task', 'Last Task', 'mdi:format-list-bulleted'],
  ];
  for (const [block, metric, title, glyph] of fields) {
    const ref = blockRefs(group, block).find(item => item.ref.metric === metric)?.ref;
    if (ref) {
      refs.push(ref);
      rows.push(moreInfoRow(ref, `${icon(glyph)}<span>${title}</span><span>${metric === 'node_last_task' ? value(ref) : withUnit(ref)}</span>`));
    }
  }
  return rowsCard('Node Info', rows, refs, 'mdi:information-outline', MORE_INFO_ROW_CSS
    + 'nav > :is(a, article) > ha-icon { color: #ef7d00; }' + PVE_TOP_CARD_CSS);
}
const MORE_INFO_ROW_CSS = 'nav > a[title="PVE more-info"] { cursor: pointer; } nav > a[title="PVE more-info"] > span:last-child { text-align: right; font-variant-numeric: tabular-nums; }';
const moreInfoRow = miniPanelLink;
function buildDiagnosticsBlock(group) {
  const temperatures = new Set(blockRefs(group, 'temperatures').map(({ref}) => ref.entity_id)), seen = new Set();
  const items = blockRefs(group, 'diagnostics').filter(({resource, ref}) => {
    if (!['sidecar', 'zfs', 'disks'].includes(ref.metric) || temperatures.has(ref.entity_id)) return false;
    const key = `${ref.metric}:${resource.resource_id || ref.entity_id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return rowsCard('Diagnostics', items.map(({resource, ref}) => {
    const title = ref.metric === 'sidecar' ? 'Sidecar' : ref.metric === 'zfs' ? `ZFS · ${logicalName(resource, 'zfs', 'Pool')}` : logicalName(resource, 'disks', 'Disk');
    return moreInfoRow(ref, `${icon(ref.metric === 'disks' ? 'mdi:harddisk' : ref.metric === 'zfs' ? 'mdi:database-check' : 'mdi:connection')}<span>${text(title)}</span><span>${ref.metric === 'disks' ? withUnit(ref) : statusValue(ref)}</span>`);
  }), items.map(item => item.ref), 'mdi:tools', MORE_INFO_ROW_CSS);
}
function buildPveNodeView(group, opts, basePath) {

  const sections = [
    {
      type: 'grid',
      column_span: 3,
      cards: [buildPveNodeHeader(group)]
    }
  ];

  const topCards = [
    buildNodeHealthBlock(group),
    buildTemperatureBlock(group),
    buildNodeInfoBlock(group),
  ];
  const lowerSections = [
    [
      buildStorageSummaryBlock(group, basePath),
      opts.show_diagnostics ? buildDiagnosticsBlock(group) : null,
      buildReplicationBlock(group, basePath),
    ],
    [
      buildGuestSummaryBlock(group, 'ct', basePath),
    ],
    [
      buildGuestSummaryBlock(group, 'vm', basePath),
    ],
  ];

  for (const card of topCards) {
    if (card) sections.push({type: 'grid', cards: [card]});
  }
  for (const cards of lowerSections.map(items => items.filter(Boolean))) {
    if (cards.length) sections.push({type: 'grid', cards});
  }

  return darkView({
    title: group.node || group.entry_id,
    path: nodeViewPath(group),
    icon: ICONS.pve,
    type: 'sections',
    max_columns: 3,
    sections
  });
}

function guestDetailCards(resource, block, layout, opts, hass) {
  const title = kind => hass.localize?.(`ui.panel.config.devices.entities.${kind}`)
    || (hass.language?.startsWith('en') ? {control: 'Controls', sensor: 'Sensors'}
      : {control: 'Controles', sensor: 'Sensores'})[kind];
  const buttons = resource.references.filter(ref => ref.entity_id.startsWith('button.'));
  const cards = resourceCards({...resource, references: resource.references.filter(ref => !ref.entity_id.startsWith('button.'))}, block, layout, opts)
    .map(card => card.type === 'entities' ? styled({...card, title: title('sensor'),
      entities: card.entities.map(row => row.attribute ? row : {...row, name: {type: 'entity'}})}, layout) : card);
  if (opts.show_maintenance_controls && buttons.length) {
    // Native button entity rows retain HA availability and its press control.
    // Confirm both the row action and the native press button.
    cards.unshift(styled({type: 'entities', title: title('control'), show_header_toggle: false,
      entities: buttons.map(ref => {
        const confirmation = {text: `Run ${label(ref)} on ${resource.title}?`};
        return {entity: ref.entity_id, name: {type: 'entity'}, confirmation,
          tap_action: {action: 'perform-action', perform_action: 'button.press',
            target: {entity_id: ref.entity_id}, confirmation},
          hold_action: {action: 'none'}, double_tap_action: {action: 'none'}};
      })}, layout));
  }
  return cards;
}

// PBS uses the shared presentation helpers, but only PBS model metrics.
const PBS_ROW_CSS = MORE_INFO_ROW_CSS + 'nav > a > ha-icon { color: #ef7d00; } h3 { font: inherit; color: #b7c2cc; margin: 16px 0 8px; overflow-wrap: anywhere; }';
function buildPbsHeader(group) {
  const refs = [...blockRefs(group, 'header'), ...blockRefs(group, 'server_health')].map(item => item.ref);
  const selected = [], facts = [];
  for (const [metric, title] of [['version', 'Version'], ['release', 'Release'], ['auth_status', 'Auth']]) {
    const ref = refs.find(item => item.metric === metric);
    if (!ref) continue;
    selected.push(ref);
    facts.push(`<div><span>${title}</span><strong>${value(ref)}</strong></div>`);
  }
  return {...pveMarkdown(null, `<header><div><img src="/proxmox_sensors/dashboard/logo_small.png" alt="Proxmox Extended Sensors" width="56">${icon('mdi:backup-restore')}<strong>${text(group.server_id)} · Proxmox Backup Server</strong></div><aside>${facts.join('')}</aside></header>`, selected),
    grid_options: {columns: 'full', rows: 'auto'}};
}
function pbsMetricCard(group, block, title, glyph, fields, extra = []) {
  const resources = [...(group.blocks[block] || []), ...extra], selected = [], parts = [];
  for (const resource of resources) {
    const rows = [];
    for (const [metric, name, rowIcon] of fields) {
      for (const ref of resource.references.filter(ref => ref.metric === metric && !ref.entity_id.startsWith('button.'))) {
        selected.push(ref);
        rows.push(moreInfoRow(ref, `${icon(rowIcon || glyph)}<span>${name}</span><span>${withUnit(ref)}</span>`));
      }
    }
    if (rows.length) parts.push(`${resource.kind === 'datastore' ? `<h3>${text(resource.title)}</h3>` : ''}<nav>${rows.join('')}</nav>`);
  }
  return parts.length ? pveMarkdown(title, parts.join(''), selected, glyph, PBS_ROW_CSS) : null;
}
function buildPbsActions(group, opts) {
  if (!opts.show_maintenance_controls) return null;
  const entities = [];
  for (const resource of group.blocks.maintenance || []) {
    const buttons = resource.references.filter(ref => ref.entity_id.startsWith('button.'));
    if (!buttons.length) continue;
    entities.push({type: 'section', label: resource.title});
    for (const ref of buttons) {
      const confirmation = {text: `Run ${label(ref)} on ${resource.title}?`};
      entities.push({entity: ref.entity_id, name: {type: 'entity'}, confirmation,
        tap_action: {action: 'perform-action', perform_action: 'button.press', target: {entity_id: ref.entity_id}, confirmation},
        hold_action: {action: 'none'}, double_tap_action: {action: 'none'}});
    }
  }
  return entities.length ? {type: 'entities', title: 'Actions', show_header_toggle: false, entities,
    card_mod: {style: PVE_CSS + 'ha-card { --card-mod-icon-color: #ef7d00; }'}} : null;
}
function buildPbsSections(group, opts) {
  const sections = [{type: 'grid', column_span: 3, cards: [buildPbsHeader(group)]}];
  const cards = [
    pbsMetricCard(group, 'server_health', 'Server Health', 'mdi:pulse',
      [['cpu_usage', 'CPU'], ['ram_usage', 'RAM'], ['ram_used', 'RAM Used'], ['ram_total', 'RAM Total'], ['ram_free', 'RAM Free']]),
    pbsMetricCard(group, 'datastores', 'Datastore', 'mdi:database',
      [['datastore_usage', 'Usage'], ['datastore_total', 'Total'], ['datastore_used', 'Used'], ['datastore_free', 'Free'], ['dedup', 'Dedup']]),
    pbsMetricCard(group, 'backups', 'Backup Info', 'mdi:backup-restore',
      [['backups_summary', 'Backups'], ['backup_errors', 'Errors'], ['last_backup_time', 'Last Backup'], ['last_backup_size', 'Last Size'], ['last_backup_status', 'Status']]),
    pbsMetricCard(group, 'maintenance', 'Maintenance', 'mdi:tools',
      [['gc_status', 'GC'], ['prune_status', 'Prune'], ['verify_status', 'Verify'], ['last_action', 'Last Action']],
      (group.blocks.tasks || []).filter(resource => resource.kind === 'datastore')),
    pbsMetricCard(group, 'tasks', 'Last Task', 'mdi:format-list-bulleted',
      [['last_task', 'Task'], ['last_task_type', 'Type'], ['last_task_status', 'Status'], ['last_task_duration', 'Duration'], ['last_task_message', 'Message']]),
    buildPbsActions(group, opts),
  ];
  for (const card of cards) if (card) sections.push({type: 'grid', cards: [card]});
  return sections;
}

function clusterRef(group, block, metric) {
  return blockRefs(group, block).find(({ref}) => ref.metric === metric && !ref.job_id)?.ref;
}
function buildClusterHeader(group) {
  const ref = clusterRef(group, 'header', 'status');
  const status = ref ? moreInfoRow(ref, `<div><span>Status</span><strong>${value(ref)}</strong></div>`) : '';
  return {...pveMarkdown(null, `<header><div><img src="/proxmox_sensors/dashboard/logo_small.png" alt="Proxmox Extended Sensors" width="56">${icon('mdi:server-network')}<strong>${text(group.cluster_id)} · Proxmox Cluster</strong></div><aside>${status}</aside></header>`, ref ? [ref] : [], 'mdi:server-network',
    'aside > a { color: inherit; text-decoration: none; cursor: pointer; } aside > a > div { display: flex; flex-direction: column; gap: 6px; } aside span { color: #b7c2cc; }'),
    grid_options: {columns: 'full', rows: 'auto'}};
}
function clusterMetricCard(group, title, glyph, fields, detailRows = [], detailRefs = []) {
  const rows = [], refs = [];
  for (const [block, metric, name, rowIcon] of fields) {
    const ref = clusterRef(group, block, metric);
    if (!ref || refs.some(item => item.entity_id === ref.entity_id)) continue;
    refs.push(ref);
    rows.push(moreInfoRow(ref, `${icon(rowIcon || glyph)}<span>${name}</span><span>${withUnit(ref)}</span>`));
  }
  return rowsCard(title, [...rows, ...detailRows], [...refs, ...detailRefs], glyph,
    MORE_INFO_ROW_CSS + 'nav > a > ha-icon { color: #ef7d00; }');
}
function clusterSyncTime(ref, hass) {
  const state = hass.states?.[ref.entity_id];
  const raw = ref.attribute ? state?.attributes?.[ref.attribute] : state?.state;
  // Replication sync sensors expose timestamp states. Reject missing/invalid
  // values; never turn a numeric sensor value into an epoch date.
  if (typeof raw !== 'string' || !raw.includes('T')) return value(ref);
  const date = new Date(raw);
  if (!Number.isFinite(date.getTime())) return value(ref);
  try {
    const zone = hass.locale?.time_zone === 'local' ? undefined : hass.config?.time_zone;
    const formatted = new Intl.DateTimeFormat(hass.locale?.language || hass.language || undefined,
      {dateStyle: 'short', timeStyle: 'short', ...(zone ? {timeZone: zone} : {})}).format(date);
    return text(formatted);
  } catch { return value(ref); }
}
function buildClusterReplication(group, hass) {
  const details = blockRefs(group, 'replication').filter(({ref}) => ref.job_id
    && ['duration', 'last_sync', 'next_sync'].includes(ref.metric));
  const jobs = clusterRef(group, 'replication', 'jobs');
  const state = jobs && hass.states?.[jobs.entity_id];
  const count = jobs?.attribute ? state?.attributes?.[jobs.attribute] : state?.state;
  const positive = (typeof count === 'string' && count.trim() !== '' || typeof count === 'number')
    && Number.isFinite(Number(count)) && Number(count) > 0;
  if (!positive && !details.length) return null;
  const rows = details.map(({resource, ref}) => {
    const knownGuest = ['ct', 'vm'].includes(resource.kind) && resource.guest_id != null;
    let context = knownGuest ? `${resource.kind === 'ct' ? 'CT' : 'VM'} ${resource.guest_id}` : `Job ${ref.job_id}`;
    const jobs = new Set(details.filter(item => item.resource.resource_id === resource.resource_id).map(item => item.ref.job_id));
    if (knownGuest && jobs.size > 1) context += ` · ${ref.job_id}`;
    const metric = {duration: 'Duration', last_sync: 'Last sync', next_sync: 'Next sync'}[ref.metric];
    return moreInfoRow(ref, `${icon('mdi:content-copy')}<span>${text(`${context} · ${metric}`)}</span><span>${ref.metric === 'duration' ? withUnit(ref) : clusterSyncTime(ref, hass)}</span>`);
  });
  return clusterMetricCard(group, 'Replication', 'mdi:content-copy',
    [['replication', 'jobs', 'Jobs'], ['replication', 'status', 'Status']], rows, details.map(item => item.ref));
}
function buildClusterSections(group, hass) {
  const sections = [{type: 'grid', column_span: 3, cards: [buildClusterHeader(group)]}];
  const cards = [
    clusterMetricCard(group, 'Cluster Health', 'mdi:heart-pulse', [
      ['cluster_health', 'cpu_usage', 'CPU', 'mdi:cpu-64-bit'], ['cluster_health', 'ram_usage', 'RAM', 'mdi:memory'],
      ['tasks', 'failed_tasks', 'Failed Tasks', 'mdi:alert-circle']]),
    clusterMetricCard(group, 'Resources', 'mdi:server', [
      ['nodes', 'nodes_online', 'Nodes'], ['guests', 'cts_running', 'CTs', 'mdi:chip'], ['guests', 'vms_running', 'VMs', 'mdi:monitor']]),
    clusterMetricCard(group, 'System', 'mdi:cog-outline', [
      ['storage', 'storage_usage', 'Storage', 'mdi:database'], ['diagnostics', 'firewall', 'Firewall', 'mdi:shield']]),
    clusterMetricCard(group, 'Backup Health', 'mdi:backup-restore', [
      ['backup_health', 'backup_jobs', 'Jobs'], ['backup_health', 'backup_age', 'Age', 'mdi:clock-outline'], ['backup_health', 'backup_health', 'Health']]),
    buildClusterReplication(group, hass),
  ];
  for (const card of cards) if (card) sections.push({type: 'grid', cards: [card]});
  return sections;
}

export function generateDashboard(payload, config = {}, basePath = null, hass = {}) {
  if (payload.schema_version !== 1) throw new Error("Unsupported Proxmox dashboard schema");
  const opts = options(config);
  const views = [];
  const subviews = new Map();
  for (const family of FAMILIES) {
    if (!opts.dashboards.includes(family) || !payload.available_dashboard_types.includes(family)) continue;
    const layout = payload.layouts[family];
    const model = payload.models[family];
    if (!layout || !model) continue;
    const groups = family === "pve" ? [...model.groups].sort((a, b) =>
      (a.node || a.entry_id || "").localeCompare(b.node || b.entry_id || "", undefined,
        {numeric: true, sensitivity: "base"})) : model.groups;
    for (const group of groups) {
      if (family === 'pbs') {
        const sections = buildPbsSections(group, opts);
        views.push(darkView({title: group.server_id || TITLES[family], path: `pbs-${encodePathPart(group.entry_id)}`,
          icon: ICONS[family], type: "sections", max_columns: 3, sections}));
        continue;
      }
      if (family === 'cluster') {
        const sections = buildClusterSections(group, hass);
        views.push(darkView({title: group.cluster_id || TITLES[family], path: `cluster-${encodePathPart(group.entry_id)}`,
          icon: ICONS[family], type: "sections", max_columns: 3, sections}));
        continue;
      }
      const sections = [];
      const mainPath = nodeViewPath(group);
      const groupTitle = group.node || group.server_id || group.cluster_id || group.entry_id;
      for (const block of layout.blocks) {
        // Only detail subviews use the layout renderer for PVE. Its main view
        // is composed independently below, never from the generic header.
        if (family === "pve" && !["guests", "storage"].includes(block.id)) continue;
        if (block.id === "diagnostics" && !opts.show_diagnostics) continue;
        const cards = (group.blocks[block.id] || []).flatMap(resource => {
          if (family !== "pve" || !["guests", "storage"].includes(block.id)) {
            return resourceCards(resource, block, layout, opts);
          }
          if (!resource.references.length) return [];
          if (!basePath) throw new Error("Open this strategy in its Lovelace dashboard to resolve subview navigation");
          const path = resourceSubviewPath(resource);
          const detailCards = block.id === 'guests' ? guestDetailCards(resource, block, layout, opts, hass)
            : resourceCards(resource, block, layout, opts);
          const sections = [{type: "grid", cards: [styled({type: "heading", heading: resourceTitle(resource),
            heading_style: "title", icon: block.icon}, layout, "header_card"), ...detailCards]}];
          if (block.id === "guests") {
            const related = (group.blocks.replication || []).filter(item => item.resource_id === resource.resource_id);
            const replicationBlock = layout.blocks.find(item => item.id === "replication");
            if (related.length && replicationBlock) {
              const replicationCards = related.flatMap(item => resourceCards(item, replicationBlock, layout, opts));
              if (replicationCards.length) sections.push({type: "grid", cards: [
                styled({type: "heading", heading: replicationBlock.title, icon: replicationBlock.icon,
                  heading_style: "title"}, layout, "header_card"), ...replicationCards]});
            }
          }
          subviews.set(path, darkView({title: resourceTitle(resource), path, type: "sections", subview: true,
            back_path: `${basePath}/${mainPath}`, max_columns: 3, sections}));
          return [];
        });
        if (!cards.length) continue;
        sections.push({type: "grid", cards: [
          styled({type: "heading", heading: `${groupTitle} · ${block.title}`, icon: block.icon,
            heading_style: "title"}, layout, "header_card"), ...cards]});
      }
      if (family === "pve") views.push(buildPveNodeView(group, opts, basePath));
    }
  }
  // A valid native empty view provides feedback without inventing resource data.
  if (!views.length) views.push(darkView({title: "Proxmox", path: "proxmox", type: "sections", sections: [
    {type: "grid", cards: [{type: "markdown", content: "No representable Proxmox resources for the selected families."}]}]}));
  return {title: "Proxmox Extended Sensors", views: [...views, ...subviews.values()]};
}

export class ProxmoxDashboardStrategy extends HTMLElement {
  static noEditor = true;
  static getCreateSuggestions(_hass) { return {title: "Proxmox Extended Sensors", icon: "mdi:server"}; }
  static async generate(config, hass) {
    options(config); // Reject invalid configuration before requesting a snapshot.
    const payload = await hass.callWS({type: "proxmox_sensors/dashboard_models"});
    return generateDashboard(payload, config, dashboardBasePath(window.location?.pathname || "", hass.panels), hass);
  }
}

const elementName = "ll-strategy-dashboard-proxmox-sensors";
if (!customElements.get(elementName)) customElements.define(elementName, ProxmoxDashboardStrategy);
window.customStrategies = window.customStrategies || [];
if (!window.customStrategies.some(item => item.type === TYPE && item.strategyType === "dashboard")) {
  window.customStrategies.push({type: TYPE, strategyType: "dashboard", name: "Proxmox Extended Sensors",
    description: "Generated PVE, PBS and Cluster dashboards from your configured Proxmox resources.",
    documentationURL: "https://github.com/Javisen/proxmox_sensors"});
}
