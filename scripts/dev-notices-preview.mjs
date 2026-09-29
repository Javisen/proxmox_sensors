import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdir, mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const rootDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const astroEntry = path.join(rootDirectory, "node_modules/astro/bin/astro.mjs");
const previewParent = path.join(rootDirectory, ".astro");
await mkdir(previewParent, { recursive: true });
const previewDirectory = await mkdtemp(path.join(previewParent, "notices-preview-"));
const host = "127.0.0.1";
const port = 4321;

function run(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, options);
    child.on("error", reject);
    child.on("exit", (code, signal) => {
      if (signal) reject(new Error(`Preview build stopped by ${signal}`));
      else if (code === 0) resolve();
      else reject(new Error(`Preview build exited with code ${code}`));
    });
  });
}

async function resolveFile(requestUrl) {
  const pathname = decodeURIComponent(new URL(requestUrl, `http://${host}:${port}`).pathname);
  const relativePath = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
  const candidate = path.resolve(previewDirectory, `.${relativePath}`);
  const relativeCandidate = path.relative(previewDirectory, candidate);

  if (relativeCandidate.startsWith("..") || path.isAbsolute(relativeCandidate)) return null;

  try {
    const details = await stat(candidate);
    return details.isDirectory() ? path.join(candidate, "index.html") : candidate;
  } catch {
    return null;
  }
}

try {
  await run(process.execPath, [astroEntry, "build", "--outDir", previewDirectory], {
    cwd: rootDirectory,
    env: { ...process.env, PROJECT_NOTICES_PREVIEW: "warning-active" },
    stdio: "inherit",
  });

  const server = createServer(async (request, response) => {
    const filePath = await resolveFile(request.url ?? "/");
    if (!filePath) {
      response.writeHead(404).end("Not found");
      return;
    }

    const extension = path.extname(filePath);
    const contentType = extension === ".html"
      ? "text/html; charset=utf-8"
      : extension === ".css"
        ? "text/css; charset=utf-8"
        : extension === ".js"
          ? "text/javascript; charset=utf-8"
          : "application/octet-stream";

    response.writeHead(200, { "Content-Type": contentType });
    response.end(await readFile(filePath));
  });

  server.listen(port, host, () => {
    console.log(`Project Notices preview: http://${host}:${port}/`);
  });

  const stop = () => server.close(async () => {
    await rm(previewDirectory, { recursive: true, force: true });
    process.exit(0);
  });
  process.once("SIGINT", stop);
  process.once("SIGTERM", stop);
} catch (error) {
  await rm(previewDirectory, { recursive: true, force: true });
  throw error;
}
