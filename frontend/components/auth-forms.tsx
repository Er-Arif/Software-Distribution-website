"use client";

import { useState } from "react";
import { apiBase } from "@/lib/api";

export function LoginForm() {
  const [email, setEmail] = useState("customer@example.com");
  const [password, setPassword] = useState("CustomerPass123!");
  const [message, setMessage] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Signing in...");
    const response = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setMessage("Login failed");
      return;
    }
    const data = await response.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setMessage("Signed in. Dashboard pages can now load your data.");
  }

  return (
    <form onSubmit={submit} className="mt-6 space-y-4 rounded-md border border-slate-200 bg-white p-5">
      <input className="w-full rounded-md border border-slate-300 px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" type="email" />
      <input className="w-full rounded-md border border-slate-300 px-3 py-2" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
      <button className="w-full rounded-md bg-brand px-4 py-2 font-semibold text-white">Sign in</button>
      {message ? <p className="text-sm text-slate-600">{message}</p> : null}
    </form>
  );
}
