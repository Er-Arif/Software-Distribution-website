import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerSupportPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Support</h1>
      <div className="mt-6">
        <ResourceTable title="Support Tickets" path="/customer/support-tickets" />
      </div>
    </DashboardShell>
  );
}
