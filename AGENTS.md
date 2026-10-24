# Development page updates

When asked “Actualiza la parte de desarrollo en la web con las últimas correcciones y mejoras”:

1. Review the latest relevant fixes and improvements in this repository and their issue or pull request evidence. Update only entries whose facts and current status are supported; do not infer completion, testing, progress, or a new release version.
2. Edit `website/development.json` as the single source for roadmap entries. Keep each item's existing `id`, `active`, `status`, `progress`, English `title` and `message`, and Spanish `es.title` and `es.message` unless evidence calls for a change. Translate each changed entry in the same edit. Preserve unrelated entries.
3. Use only the item statuses defined in `scripts/project-development.mjs`: `idea`, `study`, `planned`, `development`, `testing`, `completed`, `paused`, `cancelled`. Release statuses are `planning`, `development`, `testing`, `completed`, `paused`. Use `null` for progress when no measured percentage is available.
4. `src/i18n/content.ts` contains fixed page text. Add a translation there only when fixed page text changes; roadmap entry text belongs in `development.json`.
5. Run `npm run development:check` and `npm run build`. Review the English and Spanish Development pages in the build output. Report the evidence, changes, and test result. Do not commit, push, or publish without the user's authorization.

The Pages workflow builds on pushes to `main`; `prebuild` validates the data and translations, and `postbuild` checks the generated English and Spanish pages. A failed check or build prevents deployment.
