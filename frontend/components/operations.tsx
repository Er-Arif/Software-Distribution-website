"use client";

import { useEffect, useState } from "react";
import { apiBase } from "@/lib/api";

type Option = { id: string; name?: string; email?: string; code?: string; slug?: string; version?: string };
type Message = { type: "ok" | "error"; text: string };

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

async function apiPost(path: string, body: Record<string, unknown>) {
  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed: ${response.status}`);
  return data;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function Notice({ message }: { message: Message | null }) {
  if (!message) return null;
  return (
    <p className={`mt-3 text-sm ${message.type === "ok" ? "text-emerald-700" : "text-red-700"}`}>
      {message.text}
    </p>
  );
}

export function CustomerSupportComposer() {
  const [subject, setSubject] = useState("Activation help");
  const [body, setBody] = useState("I need help with my license activation.");
  const [priority, setPriority] = useState("normal");
  const [message, setMessage] = useState<Message | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiPost("/support/tickets", { subject, body, priority });
      setMessage({ type: "ok", text: "Support ticket created." });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Ticket failed." });
    }
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Open Support Ticket</h2>
      <div className="mt-4 grid gap-3">
        <input className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={subject} onChange={(event) => setSubject(event.target.value)} />
        <select className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={priority} onChange={(event) => setPriority(event.target.value)}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
        <textarea className="min-h-28 rounded-md border border-slate-300 px-3 py-2 text-sm" value={body} onChange={(event) => setBody(event.target.value)} />
      </div>
      <button className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white">Create ticket</button>
      <Notice message={message} />
    </form>
  );
}

export function CustomerDownloadActions() {
  const [downloads, setDownloads] = useState<Record<string, string | number>[]>([]);
  const [message, setMessage] = useState<Message | null>(null);

  useEffect(() => {
    apiGet<Record<string, string | number>[]>("/customer/available-downloads")
      .then(setDownloads)
      .catch((error: Error) => setMessage({ type: "error", text: error.message }));
  }, []);

  async function createLink(buildId: string) {
    try {
      const response = await apiGet<{ url: string; expires_at: string }>(`/downloads/builds/${buildId}/signed-url`);
      setMessage({ type: "ok", text: `Signed link created, expires ${new Date(response.expires_at).toLocaleString()}.` });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Download failed." });
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Available Installers</h2>
      <div className="mt-4 space-y-3">
        {downloads.length === 0 ? <p className="text-sm text-slate-500">No entitled installers available.</p> : null}
        {downloads.map((item) => (
          <div key={String(item.build_id)} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-100 p-3 text-sm">
            <div>
              <div className="font-medium">{item.product} {item.version}</div>
              <div className="text-slate-500">{item.os} {item.architecture} {item.installer_type}</div>
            </div>
            <button onClick={() => createLink(String(item.build_id))} className="rounded-md border border-slate-300 px-3 py-2 font-medium">
              Create signed link
            </button>
          </div>
        ))}
      </div>
      <Notice message={message} />
    </section>
  );
}

export function AdminLicenseGrant() {
  const [customers, setCustomers] = useState<Option[]>([]);
  const [products, setProducts] = useState<Option[]>([]);
  const [plans, setPlans] = useState<Option[]>([]);
  const [policies, setPolicies] = useState<Option[]>([]);
  const [message, setMessage] = useState<Message | null>(null);

  useEffect(() => {
    Promise.all([
      apiGet<Option[]>("/admin/customers"),
      apiGet<Option[]>("/admin/products"),
      apiGet<Option[]>("/admin/plans"),
      apiGet<Option[]>("/admin/policies")
    ]).then(([customerRows, productRows, planRows, policyRows]) => {
      setCustomers(customerRows.filter((row) => !String(row.email || "").includes("admin")));
      setProducts(productRows);
      setPlans(planRows);
      setPolicies(policyRows);
    }).catch((error: Error) => setMessage({ type: "error", text: error.message }));
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const created = await apiPost("/admin/licenses", {
        user_id: form.get("user_id"),
        product_id: form.get("product_id"),
        plan_id: form.get("plan_id") || null,
        policy_id: form.get("policy_id"),
        source: "manual"
      });
      setMessage({ type: "ok", text: `License granted: ${created.key}` });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Grant failed." });
    }
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Grant Manual License</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Select name="user_id" items={customers} label={(item) => item.email || item.name || item.id} />
        <Select name="product_id" items={products} label={(item) => item.name || item.slug || item.id} />
        <Select name="plan_id" items={plans} label={(item) => item.code || item.name || item.id} />
        <Select name="policy_id" items={policies} label={(item) => item.name || item.id} />
      </div>
      <button className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white">Grant license</button>
      <Notice message={message} />
    </form>
  );
}

export function AdminReleaseCreator() {
  const [products, setProducts] = useState<Option[]>([]);
  const [message, setMessage] = useState<Message | null>(null);

  useEffect(() => {
    apiGet<Option[]>("/admin/products").then(setProducts).catch((error: Error) => setMessage({ type: "error", text: error.message }));
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const created = await apiPost("/admin/versions", {
        product_id: form.get("product_id"),
        version: form.get("version"),
        status: "draft",
        forced_update: form.get("forced_update") === "on",
        optional_update: true
      });
      setMessage({ type: "ok", text: `Draft release created: ${created.id}` });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Release failed." });
    }
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Create Draft Release</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Select name="product_id" items={products} label={(item) => item.name || item.slug || item.id} />
        <input name="version" required placeholder="2.0.0" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
        <label className="flex items-center gap-2 text-sm"><input name="forced_update" type="checkbox" /> Forced update</label>
      </div>
      <button className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white">Create release</button>
      <Notice message={message} />
    </form>
  );
}

export function AdminLegalPublisher() {
  const [message, setMessage] = useState<Message | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiPost("/admin/legal", {
        document_type: form.get("document_type"),
        title: form.get("title"),
        body: form.get("body"),
        version: form.get("version"),
        publish: true
      });
      setMessage({ type: "ok", text: "Legal document published." });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Publish failed." });
    }
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Publish Legal Document</h2>
      <div className="mt-4 grid gap-3">
        <select name="document_type" className="rounded-md border border-slate-300 px-3 py-2 text-sm">
          <option value="terms">Terms</option>
          <option value="privacy">Privacy</option>
          <option value="refund">Refund</option>
          <option value="eula">EULA</option>
        </select>
        <input name="title" required placeholder="Document title" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
        <input name="version" required defaultValue="1.0" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
        <textarea name="body" required placeholder="Legal content" className="min-h-32 rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <button className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white">Publish</button>
      <Notice message={message} />
    </form>
  );
}

function Select({ name, items, label }: { name: string; items: Option[]; label: (item: Option) => string }) {
  return (
    <select name={name} required className="rounded-md border border-slate-300 px-3 py-2 text-sm">
      <option value="">Select...</option>
      {items.map((item) => (
        <option key={item.id} value={item.id}>{label(item)}</option>
      ))}
    </select>
  );
}
