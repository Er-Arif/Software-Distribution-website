import { DashboardShell } from "@/components/dashboard-shell";

export default function AdminDashboard() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Admin Dashboard</h1>
      <div className="mt-6 grid gap-5 md:grid-cols-4">
        {["Revenue", "Downloads", "Active Licenses", "Webhook Alerts"].map((label) => (
          <div key={label} className="rounded-md border border-slate-200 bg-white p-5">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-2 text-3xl font-bold">0</div>
          </div>
        ))}
      </div>
      <section className="mt-8 rounded-md border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">Critical admin safeguards</h2>
        <p className="mt-2 text-sm text-slate-600">Revoke, refund, publish, rollback, impersonation, and signing changes require confirmation and audit logging.</p>
      </section>
    </DashboardShell>
  );
}
