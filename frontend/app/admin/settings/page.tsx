import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminSettingsPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Settings</h1>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <ResourceTable title="License Policies" path="/admin/policies" />
        <ResourceTable title="Legal Content" path="/admin/legal" />
      </div>
    </DashboardShell>
  );
}
