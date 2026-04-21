import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminCustomersPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Customers</h1>
      <div className="mt-6">
        <ResourceTable title="Customers" path="/admin/customers" />
      </div>
    </DashboardShell>
  );
}
