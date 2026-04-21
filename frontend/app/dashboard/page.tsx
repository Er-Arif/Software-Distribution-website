import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerDashboard() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Customer Dashboard</h1>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <ResourceTable title="Dashboard Summary" path="/customer/dashboard" />
        <ResourceTable title="Notifications" path="/customer/notifications" />
      </div>
    </DashboardShell>
  );
}
