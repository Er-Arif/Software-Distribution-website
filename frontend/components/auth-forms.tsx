"use client";

import { useState } from "react";
import { apiBase } from "@/lib/api";

type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
};

export function LoginForm() {
  const [email, setEmail] = useState("customer@example.com");
  const [password, setPassword] = useState("CustomerPass123!");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function useSeedLogin(kind: "customer" | "admin") {
    if (kind === "admin") {
      setEmail("admin@example.com");
      setPassword("AdminPass123!");
      return;
    }
    setEmail("customer@example.com");
    setPassword("CustomerPass123!");
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("Signing in...");
    const response = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setMessage("Login failed");
      setLoading(false);
      return;
    }
    const data = await response.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    const meResponse = await fetch(`${apiBase}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` }
    });
    if (!meResponse.ok) {
      setMessage("Signed in, but profile loading failed. Open the dashboard manually.");
      setLoading(false);
      return;
    }
    const me = (await meResponse.json()) as MeResponse;
    localStorage.setItem("current_user", JSON.stringify(me));
    setMessage(`Signed in as ${me.email}. Redirecting...`);
    window.location.href = me.roles.some((role) => role === "admin" || role === "super_admin" || role === "support")
      ? "/admin"
      : "/dashboard";
  }

  return (
    <form onSubmit={submit} className="mt-6 space-y-4 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid grid-cols-2 gap-2">
        <button type="button" onClick={() => useSeedLogin("customer")} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700">
          Use Customer
        </button>
        <button type="button" onClick={() => useSeedLogin("admin")} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700">
          Use Admin
        </button>
      </div>
      <input className="w-full rounded-md border border-slate-300 px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" type="email" />
      <input className="w-full rounded-md border border-slate-300 px-3 py-2" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
      <button disabled={loading} className="w-full rounded-md bg-brand px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400">
        {loading ? "Signing in..." : "Sign in"}
      </button>
      {message ? <p className="text-sm text-slate-600">{message}</p> : null}
    </form>
  );
}
