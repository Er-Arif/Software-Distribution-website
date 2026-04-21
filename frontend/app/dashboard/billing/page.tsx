import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerBillingPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Billing</h1>
      <div className="mt-6">
        <ResourceTable title="Orders" path="/customer/billing" />
      </div>
    </DashboardShell>
  );
}
