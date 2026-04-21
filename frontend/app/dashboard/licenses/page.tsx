import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerLicensesPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Licenses</h1>
      <div className="mt-6">
        <ResourceTable title="License Keys" path="/customer/licenses" />
      </div>
    </DashboardShell>
  );
}
