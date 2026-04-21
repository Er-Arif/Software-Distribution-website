import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerProductsPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">My Products</h1>
      <div className="mt-6">
        <ResourceTable title="Purchased Products" path="/customer/products" />
      </div>
    </DashboardShell>
  );
}
