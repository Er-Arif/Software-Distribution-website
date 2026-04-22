import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminPaymentsPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Payments</h1>
      <div className="mt-6">
        <ResourceTable title="Payments" path="/admin/payments" />
      </div>
    </DashboardShell>
  );
}
