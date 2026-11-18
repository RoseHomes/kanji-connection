// Offline upload/Git boundaries. Never contacts Vercel, Supabase, or reads secret files.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ignore from "../frontend/node_modules/ignore/index.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(root, "private/deployment-review");
fs.mkdirSync(output, { recursive: true });
function require(condition, message) {
  if (!condition) throw new Error(message);
}
const git = ignore().add(
  fs.readFileSync(path.join(root, ".gitignore"), "utf8"),
);
for (const name of [
  "private/kanji-connection-extracted/chapters/chapter_01.json",
  "private/live-auth-test/password.dpapi",
  "reference/book.pdf",
  "backend/.env",
  "frontend/.env.production.local",
  "artifacts/test.json",
  "frontend/test-results/book.png",
  "backend/client.key",
]) {
  require(git.ignores(name), "Git exclusion missing for protected path");
}
for (const name of [
  "frontend/.env.production.example",
  "backend/.env.production.example",
])
  require(!git.ignores(name), "Production template must remain reviewable");
const manifest = {
  root_upload_denied: false,
  git_exclusions_passed: true,
  git_index_verified: false,
  projects: {},
};
const rootRules = ignore().add(
  fs.readFileSync(path.join(root, ".vercelignore"), "utf8"),
);
require(rootRules.ignores("private/book.json") &&
  rootRules.ignores(
    "frontend/package.json",
  ), "Repository-root uploads must be refused");
manifest.root_upload_denied = true;
for (const project of ["frontend", "backend"]) {
  const base = path.join(root, project);
  const rules = ignore().add(
    fs.readFileSync(path.join(base, ".vercelignore"), "utf8"),
  );
  for (const name of [
    ".env",
    ".env.production",
    ".env.production.example",
    "private/book.json",
    "reference/book.pdf",
    "artifacts/test.json",
    "tests/test_secret.py",
    "node_modules/secret.js",
    "public/private.json",
  ])
    require(rules.ignores(
      name,
    ), "Deployment exclusion missing for protected path");
  const included = [];
  function visit(folder, relative = "") {
    for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
      const rel = (relative ? relative + "/" : "") + entry.name;
      if (rules.ignores(rel + (entry.isDirectory() ? "/" : ""))) continue;
      require(!entry.isSymbolicLink(), "Symlinks require explicit deployment review");
      if (entry.isDirectory()) visit(path.join(folder, entry.name), rel);
      else included.push(rel);
    }
  }
  visit(base);
  require(included.includes("vercel.json"), "Project configuration omitted");
  require(!included.some((p) =>
    /(\.env|\.pdf$|\.dpapi$|\.test\.|__pycache__|test-results|playwright-report|(^|\/)private\/)/i.test(
      p,
    ),
  ), "Protected file in deployment input");
  if (project === "backend")
    require(!included.some((p) =>
      /^app\/(book|seed|editorial|json_content|content_schema|thai_references)/.test(
        p,
      ),
    ), "Import tooling must not enter runtime bundle");
  const config = JSON.parse(
    fs.readFileSync(path.join(base, "vercel.json"), "utf8"),
  );
  if (project === "frontend") {
    const pkg = JSON.parse(
      fs.readFileSync(path.join(base, "package.json"), "utf8"),
    );
    const lock = JSON.parse(
      fs.readFileSync(path.join(base, "package-lock.json"), "utf8"),
    );
    require(pkg.engines.node === "22.x" &&
      lock.packages[""].engines.node ===
        "22.x", "Node runtime pins must agree");
    const rule = new RegExp("^" + config.rewrites[0].source + "$");
    require(rule.test("/account") &&
      rule.test("/lessons/chapter-02"), "SPA/Auth callback rewrite missing");
    require(!rule.test("/api/v1/health") &&
      !rule.test("/api") &&
      !rule.test(
        "/assets/missing.js",
      ), "API/assets must never become SPA HTML");
  } else {
    require(config.functions["index.py"].excludeFiles.length <=
      256, "Function exclusion pattern exceeds platform limit");
    require(fs
      .readFileSync(path.join(base, ".python-version"), "utf8")
      .trim() === "3.13", "Python runtime pin missing");
    require(/entrypoint\s*=\s*["']index:app["']/.test(
      fs.readFileSync(path.join(base, "pyproject.toml"), "utf8"),
    ), "Hosted entrypoint must enforce deployment guards");
    require(config.headers[0].headers.some(
      (h) => h.key === "Cache-Control" && h.value.includes("no-store"),
    ), "Private API responses must not be CDN-cached");
  }
  manifest.projects[project] = {
    input_files: included.sort(),
    input_bytes: included.reduce(
      (sum, p) => sum + fs.statSync(path.join(base, p)).size,
      0,
    ),
  };
}
fs.writeFileSync(
  path.join(output, "upload-manifest.json"),
  JSON.stringify(manifest, null, 2),
);
console.log(
  JSON.stringify({
    root_upload_denied: true,
    git_ignore_rules_passed: true,
    git_index_verified: false,
    frontend_input_files: manifest.projects.frontend.input_files.length,
    backend_input_files: manifest.projects.backend.input_files.length,
    api_rewrites_checked: true,
  }),
);
