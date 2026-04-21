import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminLicensesPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Licenses</h1>
      <div className="mt-6">
        <ResourceTable title="Licenses" path="/admin/licenses" />
      </div>
    </DashboardShell>
  );
}
