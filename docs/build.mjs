import { cp, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { spawn } from "node:child_process";

const docs = resolve(import.meta.dirname);
const output = resolve(docs, "dist");
const assets = resolve(docs, "assets");

const sourcey = spawn("npx", ["sourcey", "build", "-o", "dist"], { cwd: docs, stdio: "inherit" });
const exitCode = await new Promise((resolveExit, reject) => {
  sourcey.once("error", reject);
  sourcey.once("exit", resolveExit);
});
if (exitCode !== 0) process.exitCode = exitCode;
if (process.exitCode) process.exit();
await rm(resolve(output, "assets"), { recursive: true, force: true });
await cp(assets, resolve(output, "assets"), {
  recursive: true,
  filter: (source) => !source.endsWith(".png"),
});
