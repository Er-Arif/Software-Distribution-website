const backend = process.env.BACKEND_URL || "http://localhost:8000";

async function request(method, path, options = {}) {
  const response = await fetch(`${backend}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) {
    throw new Error(`${method} ${path} failed: ${response.status} ${text}`);
  }
  return body;
}

async function login(email, password) {
  return request("POST", "/api/v1/auth/login", { body: { email, password } });
}

(async () => {
  const customer = await login("customer@example.com", "CustomerPass123!");
  const admin = await login("admin@example.com", "AdminPass123!");

  const publicChecks = [
    ["GET", "/api/v1/health"],
    ["GET", "/api/v1/health/ready"],
    ["GET", "/api/v1/metrics"],
    ["GET", "/api/v1/public/products"],
    ["GET", "/api/v1/public/products/codevault-pro"],
    ["GET", "/api/v1/public/changelog"],
    ["GET", "/api/v1/public/legal/terms"]
  ];

  const customerChecks = [
    ["GET", "/api/v1/auth/me"],
    ["GET", "/api/v1/customer/dashboard"],
    ["GET", "/api/v1/customer/products"],
    ["GET", "/api/v1/customer/available-downloads"],
    ["GET", "/api/v1/customer/licenses"],
    ["GET", "/api/v1/customer/devices"],
    ["GET", "/api/v1/customer/downloads"],
    ["GET", "/api/v1/customer/billing"],
    ["GET", "/api/v1/customer/support-tickets"],
    ["GET", "/api/v1/customer/notifications"]
  ];

  const adminChecks = [
    ["GET", "/api/v1/admin/dashboard"],
    ["GET", "/api/v1/admin/analytics"],
    ["GET", "/api/v1/admin/products"],
    ["GET", "/api/v1/admin/plans"],
    ["GET", "/api/v1/admin/policies"],
    ["GET", "/api/v1/admin/customers"],
    ["GET", "/api/v1/admin/licenses"],
    ["GET", "/api/v1/admin/orders"],
    ["GET", "/api/v1/admin/payments"],
    ["GET", "/api/v1/admin/versions"],
    ["GET", "/api/v1/admin/support-tickets"],
    ["GET", "/api/v1/admin/legal"],
    ["GET", "/api/v1/admin/feature-flags"],
    ["GET", "/api/v1/admin/entitlements"],
    ["GET", "/api/v1/admin/invoices"],
    ["GET", "/api/v1/admin/audit-logs"],
    ["GET", "/api/v1/admin/events"]
  ];

  for (const [method, path] of publicChecks) {
    await request(method, path);
  }
  for (const [method, path] of customerChecks) {
    await request(method, path, { token: customer.access_token });
  }
  for (const [method, path] of adminChecks) {
    await request(method, path, { token: admin.access_token });
  }

  const licenses = await request("GET", "/api/v1/customer/licenses", { token: customer.access_token });
  if (!Array.isArray(licenses) || licenses.length === 0) {
    throw new Error("Seed customer has no licenses.");
  }

  console.log(`API QA passed for ${publicChecks.length + customerChecks.length + adminChecks.length} endpoints.`);
})();
