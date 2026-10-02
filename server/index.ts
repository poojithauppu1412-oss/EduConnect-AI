import { spawn } from "node:child_process";
import { resolve } from "node:path";
import cors from "cors";
import express from "express";
import { clerkMiddleware } from "@clerk/express";
import { publishableKeyFromHost } from "@clerk/shared/keys";
import { createProxyMiddleware } from "http-proxy-middleware";
import {
  CLERK_PROXY_PATH,
  clerkProxyMiddleware,
  getClerkProxyHost,
} from "./middlewares/clerkProxyMiddleware";

const app = express();
const port = Number(process.env.PORT || 5000);
const apiHost = process.env.API_HOST || "127.0.0.1";
const apiPort = Number(process.env.API_PORT || 8000);
const apiOrigin = `http://${apiHost}:${apiPort}`;
const staticDirectory = resolve(process.cwd(), "frontend", "dist");

const trustedOrigins = new Set(
  (process.env.CORS_ORIGINS || "http://localhost:5000")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean),
);
for (const domain of [
  process.env.REPLIT_DEV_DOMAIN,
  ...(process.env.REPLIT_DOMAINS || "").split(","),
]) {
  if (domain?.trim()) {
    const value = domain.trim();
    trustedOrigins.add(value.includes("://") ? value : `https://${value}`);
  }
}

app.use(CLERK_PROXY_PATH, clerkProxyMiddleware());
app.use(
  cors({
    credentials: true,
    origin: (origin, callback) => {
      if (!origin || trustedOrigins.has(origin)) {
        callback(null, true);
        return;
      }
      callback(new Error("This origin is not allowed."));
    },
  }),
);
app.use(
  clerkMiddleware((req) => ({
    publishableKey: publishableKeyFromHost(
      getClerkProxyHost(req) ?? "",
      process.env.CLERK_PUBLISHABLE_KEY,
    ),
  })),
);

const apiProxy = createProxyMiddleware({
  target: apiOrigin,
  changeOrigin: false,
  pathRewrite: (path) => `/api${path}`,
});
app.use("/api", apiProxy);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(staticDirectory, { index: false }));
app.use((req, res, next) => {
  if (req.method !== "GET" || req.path.startsWith("/api/")) {
    next();
    return;
  }
  res.sendFile(resolve(staticDirectory, "index.html"));
});

const apiProcess = spawn(
  process.env.PYTHON_EXECUTABLE || "python",
  [
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    apiHost,
    "--port",
    String(apiPort),
  ],
  { env: process.env, stdio: "inherit" },
);
let stopping = false;

apiProcess.on("error", (error) => {
  console.error("FastAPI service could not be started:", error.message);
  process.exitCode = 1;
});

const server = app.listen(port, "0.0.0.0", () => {
  console.log(`EduConnect AI web server listening on port ${port}`);
});

apiProcess.on("exit", (code, signal) => {
  if (stopping) {
    return;
  }
  console.error(`FastAPI service exited unexpectedly (${code ?? signal ?? "unknown"}).`);
  server.close(() => process.exit(code && code > 0 ? code : 1));
});

for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.once(signal, () => {
    stopping = true;
    apiProcess.kill(signal);
    server.close(() => process.exit(0));
  });
}