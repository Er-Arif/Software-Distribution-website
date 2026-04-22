import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminSupportPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Support Tickets</h1>
      <div className="mt-6">
        <ResourceTable title="Tickets" path="/admin/support-tickets" />
      </div>
    </DashboardShell>
  );
}
