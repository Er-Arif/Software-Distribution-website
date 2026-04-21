"use client";

import { useEffect, useState } from "react";
import { apiBase } from "@/lib/api";

type ApiValue = string | number | boolean | null | Record<string, unknown> | Array<unknown>;

export function ResourceTable({ title, path }: { title: string; path: string }) {
  const [rows, setRows] = useState<Record<string, ApiValue>[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${apiBase}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const data = await response.json();
        if (Array.isArray(data)) return data;
        if (Array.isArray(data.orders)) return data.orders;
        return [data];
      })
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  }, [path]);

  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 6);

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      {!error && rows.length === 0 ? <p className="mt-3 text-sm text-slate-500">No records yet.</p> : null}
      {rows.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>{keys.map((key) => <th key={key} className="py-2 pr-4 font-medium">{key}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="border-b border-slate-100">
                  {keys.map((key) => (
                    <td key={key} className="max-w-64 truncate py-2 pr-4">
                      {formatValue(row[key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function formatValue(value: ApiValue | undefined) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
