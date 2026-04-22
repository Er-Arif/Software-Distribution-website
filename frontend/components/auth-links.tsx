"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type CurrentUser = {
  email: string;
  roles: string[];
};

export function AuthLinks() {
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("current_user");
    if (raw) {
      setUser(JSON.parse(raw));
    }
  }, []);

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("current_user");
    window.location.href = "/";
  }

  if (!user) {
    return <Link href="/login">Login</Link>;
  }

  const dashboardHref = user.roles.some((role) => role === "admin" || role === "super_admin" || role === "support")
    ? "/admin"
    : "/dashboard";

  return (
    <span className="flex items-center gap-4">
      <Link href={dashboardHref}>Dashboard</Link>
      <span className="hidden text-xs text-slate-500 lg:inline">{user.email}</span>
      <button onClick={logout} className="text-sm font-medium text-slate-700">
        Logout
      </button>
    </span>
  );
}
