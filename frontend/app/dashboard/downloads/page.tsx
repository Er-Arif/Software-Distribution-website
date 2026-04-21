import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerDownloadsPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Downloads</h1>
      <div className="mt-6">
        <ResourceTable title="Download Activity" path="/customer/downloads" />
      </div>
    </DashboardShell>
  );
}
