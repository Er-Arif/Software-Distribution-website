import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminDashboard() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Admin Dashboard</h1>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <ResourceTable title="Platform Summary" path="/admin/dashboard" />
        <ResourceTable title="Recent Events" path="/admin/events" />
      </div>
      <section className="mt-8 rounded-md border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">Critical admin safeguards</h2>
        <p className="mt-2 text-sm text-slate-600">Revoke, refund, publish, rollback, impersonation, and signing changes require confirmation and audit logging.</p>
      </section>
    </DashboardShell>
  );
}
