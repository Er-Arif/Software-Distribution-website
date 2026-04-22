import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminVersionsPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Versions And Releases</h1>
      <div className="mt-6">
        <ResourceTable title="Versions" path="/admin/versions" />
      </div>
    </DashboardShell>
  );
}
