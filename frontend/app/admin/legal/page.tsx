import { DashboardShell } from "@/components/dashboard-shell";
import { AdminLegalPublisher } from "@/components/operations";
import { ResourceTable } from "@/components/resource-table";

export default function AdminLegalPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Legal Content</h1>
      <div className="mt-6 grid gap-6">
        <AdminLegalPublisher />
        <ResourceTable title="Legal Documents" path="/admin/legal" />
      </div>
    </DashboardShell>
  );
}
