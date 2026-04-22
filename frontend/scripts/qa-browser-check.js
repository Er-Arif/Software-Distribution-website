const { chromium } = require("playwright-core");
const fs = require("node:fs");

const edgePath =
  process.env.BROWSER_EXECUTABLE_PATH || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const frontend = process.env.FRONTEND_URL || "http://localhost:3000";
const backend = process.env.BACKEND_URL || "http://localhost:8000";

const publicRoutes = [
  "/",
  "/products",
  "/products/codevault-pro",
  "/pricing",
  "/features",
  "/download-trial",
  "/changelog",
  "/help",
  "/about",
  "/contact",
  "/login",
  "/register",
  "/legal/terms",
  "/legal/privacy",
  "/legal/refund",
  "/legal/eula"
];

const customerRoutes = [
  "/dashboard",
  "/dashboard/products",
  "/dashboard/downloads",
  "/dashboard/licenses",
  "/dashboard/devices",
  "/dashboard/billing",
  "/dashboard/support"
];

const adminRoutes = [
  "/admin",
  "/admin/products",
  "/admin/plans",
  "/admin/versions",
  "/admin/customers",
  "/admin/licenses",
  "/admin/payments",
  "/admin/support",
  "/admin/legal",
  "/admin/analytics",
  "/admin/settings"
];

async function login(email, password) {
  const response = await fetch(`${backend}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!response.ok) {
    throw new Error(`Login failed for ${email}: ${response.status}`);
  }
  const token = await response.json();
  const meResponse = await fetch(`${backend}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token.access_token}` }
  });
  if (!meResponse.ok) {
    throw new Error(`Profile failed for ${email}: ${meResponse.status}`);
  }
  return { token, me: await meResponse.json() };
}

async function createContext(browser, session) {
  const context = await browser.newContext();
  if (session) {
    await context.addInitScript((payload) => {
      localStorage.setItem("access_token", payload.token.access_token);
      localStorage.setItem("refresh_token", payload.token.refresh_token);
      localStorage.setItem("current_user", JSON.stringify(payload.me));
    }, session);
  }
  return context;
}

async function visitRoutes(browser, label, routes, session) {
  const context = await createContext(browser, session);
  const failures = [];
  for (const route of routes) {
    const page = await context.newPage();
    const issues = [];
    page.on("console", (message) => {
      if (["error", "warning"].includes(message.type())) {
        issues.push(`console:${message.type()}:${message.text()}`);
      }
    });
    page.on("pageerror", (error) => issues.push(`pageerror:${error.message}`));
    page.on("requestfailed", (request) => {
      const url = request.url();
      if (!url.includes("/favicon.ico")) {
        issues.push(`requestfailed:${url}:${request.failure()?.errorText}`);
      }
    });
    const response = await page.goto(`${frontend}${route}`, {
      waitUntil: "networkidle",
      timeout: 30000
    });
    const status = response?.status() || 0;
    const hasCss = await page.locator("link[rel='stylesheet']").count();
    if (status >= 400 || hasCss === 0 || issues.length > 0) {
      failures.push({ label, route, status, hasCss, issues });
    }
    await page.close();
  }
  await context.close();
  return failures;
}

(async () => {
  if (!fs.existsSync(edgePath)) {
    throw new Error(`Browser executable not found. Set BROWSER_EXECUTABLE_PATH. Tried: ${edgePath}`);
  }
  const browser = await chromium.launch({
    executablePath: edgePath,
    headless: true
  });
  try {
    const customer = await login("customer@example.com", "CustomerPass123!");
    const admin = await login("admin@example.com", "AdminPass123!");
    const failures = [
      ...(await visitRoutes(browser, "public", publicRoutes, null)),
      ...(await visitRoutes(browser, "customer", customerRoutes, customer)),
      ...(await visitRoutes(browser, "admin", adminRoutes, admin))
    ];
    if (failures.length > 0) {
      console.error(JSON.stringify(failures, null, 2));
      process.exit(1);
    }
    console.log(`Browser QA passed for ${publicRoutes.length + customerRoutes.length + adminRoutes.length} routes.`);
  } finally {
    await browser.close();
  }
})();
