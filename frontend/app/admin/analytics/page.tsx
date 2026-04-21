import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminAnalyticsPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Analytics</h1>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <ResourceTable title="Orders" path="/admin/orders" />
        <ResourceTable title="Payments" path="/admin/payments" />
      </div>
    </DashboardShell>
  );
}
