import { spawn, spawnSync } from "node:child_process";

const children = [];
let stopping = false;

function start(command, args) {
  const child = spawn(command, args, {
    stdio: "inherit",
    detached: process.platform !== "win32"
  });
  children.push(child);
  child.on("exit", (code, signal) => {
    if (stopping) return;
    const reason = signal ? `signal ${signal}` : `code ${code ?? 1}`;
    console.error(`${command} exited with ${reason}; stopping the other service.`);
    stop(code ?? 1);
  });
  return child;
}

function terminate(child) {
  if (!child.pid || child.exitCode !== null) return;
  try {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
        stdio: "ignore"
      });
    } else {
      process.kill(-child.pid, "SIGTERM");
    }
  } catch {
    // The process may already have exited.
  }
}

function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;
  children.forEach(terminate);
  setTimeout(() => process.exit(exitCode), 250);
}

process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));
process.on("uncaughtException", (error) => {
  console.error(error);
  stop(1);
});

start("backend/venv/bin/uvicorn", [
  "app.main:app",
  "--app-dir",
  "backend",
  "--reload"
]);
start("npm", ["--prefix", "frontend", "run", "dev"]);
