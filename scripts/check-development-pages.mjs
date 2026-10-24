import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = JSON.parse(readFileSync(new URL("../website/development.json", import.meta.url), "utf8"));
const pages = {
  en: readFileSync(new URL("../dist/development/index.html", import.meta.url), "utf8"),
  es: readFileSync(new URL("../dist/es/development/index.html", import.meta.url), "utf8"),
};

for (const item of source.items.filter((entry) => entry.active)) {
  for (const locale of ["en", "es"]) {
    const page = pages[locale];
    const title = locale === "es" ? item.es.title : item.title;
    const message = locale === "es" ? item.es.message : item.message;
    const heading = `<h2 id="development-${item.id}">${title}</h2>`;
    assert.ok(page.includes(heading), `${locale} page is missing the title for ${item.id}`);
    assert.ok(page.includes(`<p class="roadmap-item__message">${message}</p>`),
      `${locale} page is missing the message for ${item.id}`);
  }
}

console.log("Development pages contain every active title and message in English and Spanish.");
