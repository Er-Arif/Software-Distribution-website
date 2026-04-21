import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function AdminProductsPage() {
  return (
    <DashboardShell mode="admin">
      <h1 className="text-3xl font-bold">Products</h1>
      <div className="mt-6">
        <ResourceTable title="Products" path="/admin/products" />
      </div>
    </DashboardShell>
  );
}
