import { DashboardShell } from "@/components/dashboard-shell";
import { ResourceTable } from "@/components/resource-table";

export default function CustomerDevicesPage() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Devices</h1>
      <div className="mt-6">
        <ResourceTable title="Activated Devices" path="/customer/devices" />
      </div>
    </DashboardShell>
  );
}
