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
  root_inputs_restricted: false,
  git_exclusions_passed: true,
  git_index_verified: false,
  projects: {},
};
const rootRules = ignore().add(
  fs.readFileSync(path.join(root, ".vercelignore"), "utf8"),
);
require(rootRules.ignores("private/book.json") &&
  rootRules.ignores("backend/migrations/env.py") &&
  rootRules.ignores("docs/README.md"), "Unrelated repository inputs must be excluded");
manifest.root_inputs_restricted = true;
const requiredFrontendInputs = [
  ".vercelignore", "vercel.json", "package.json", "package-lock.json",
  "index.html", "tsconfig.json", "vite.config.ts", "src/main.tsx",
];
const protectedFrontendInputs = [
  ".env", ".env.production.example", "private/book.json", "reference/book.PDF",
  "artifacts/test.json", "node_modules/test.js", "dist/index.html",
  "test-results/test.png", "e2e/guest.spec.ts", "src/private/book.json",
  "src/reference/book.pdf", "src/.env.local", "src/source.PDF",
  "src/client.key", "src/client.pem", "src/client.crt", "src/client.pfx",
  "src/password.dpapi", "src/credentials.json", "src/local.sqlite3",
  "src/content.json", "src/Home.test.tsx", "src/test-setup.ts",
];
let frontendPathBaseChecks = 0;
let backendPathBaseChecks = 0;
const requiredBackendInputs = [
  ".vercelignore", "vercel.json", "index.py", "pyproject.toml",
  ".python-version", "requirements.txt", "app/__init__.py", "app/main.py",
  "app/config.py", "app/database.py", "app/auth.py", "app/learning_routes.py",
];
const protectedBackendInputs = [
  ".env", ".env.production.example", "private/book.json", "reference/book.PDF",
  "artifacts/test.json", "tests/test_api.py", "migrations/env.py", "requirements-dev.txt",
  "requirements.lock.txt", "node_modules/test.js", "app/book_import.py", "app/book_extract.py",
  "app/seed.py", "app/json_content.py", "app/editorial.py", "app/content_schema.py",
  "app/thai_references.py", "app/source.json", "app/private/book.json",
  "app/client.key", "app/client.crt", "app/local.sqlite3", "app/.env",
  "app/__pycache__/main.pyc",
];
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
  const configText = fs.readFileSync(path.join(base, "vercel.json"), "utf8");
  const config = JSON.parse(configText);
  if (project === "frontend") {
    for (const key of ["installCommand", "buildCommand"])
      require((configText.match(new RegExp(`"${key}"\\s*:`, "g")) ?? []).length === 1,
        "Frontend configuration must have exactly one install/build command");
    for (const [label, matcher] of [["root", rootRules], ["frontend", rules]]) {
      for (const prefix of ["", "frontend/"]) {
        for (const name of requiredFrontendInputs)
          require(!matcher.ignores(prefix + name), `${label} ignore omits a required frontend input`);
        for (const name of protectedFrontendInputs)
          require(matcher.ignores(prefix + name), `${label} ignore permits a protected input`);
        for (const name of included)
          require(!matcher.ignores(prefix + name), `${label} ignore omits a frontend source file`);
        frontendPathBaseChecks++;
      }
    }
    for (const name of requiredFrontendInputs)
      require(included.includes(name), "Required frontend input missing from upload manifest");
    require(config.installCommand === "npm ci --include=dev" && config.buildCommand === "npm run build",
      "Frontend install/build commands must be restored without diagnostics");
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
    for (const [label, matcher] of [["root", rootRules], ["backend", rules]]) {
      for (const prefix of ["", "backend/"]) {
        for (const name of requiredBackendInputs)
          require(!matcher.ignores(prefix + name), `${label} ignore omits a required backend input`);
        for (const name of protectedBackendInputs)
          require(matcher.ignores(prefix + name), `${label} ignore permits a protected backend input`);
        for (const name of included)
          require(!matcher.ignores(prefix + name), `${label} ignore omits a backend runtime file`);
        backendPathBaseChecks++;
      }
    }
    for (const name of requiredBackendInputs)
      require(included.includes(name), "Required backend input missing from upload manifest");
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
    root_inputs_restricted: true,
    git_ignore_rules_passed: true,
    git_index_verified: false,
    frontend_input_files: manifest.projects.frontend.input_files.length,
    backend_input_files: manifest.projects.backend.input_files.length,
    api_rewrites_checked: true,
    frontend_path_base_checks: frontendPathBaseChecks,
    backend_path_base_checks: backendPathBaseChecks,
  }),
);
