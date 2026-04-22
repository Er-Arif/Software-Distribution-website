import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminPlansPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Plans</h1>
      <div className="mt-6">
        <ResourceTable title="Pricing Plans" path="/admin/plans" />
      </div>
    </DashboardShell>
  );
}
