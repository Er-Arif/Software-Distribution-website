import { DashboardShell } from "@/components/dashboard-shell";

export default function CustomerDashboard() {
  return (
    <DashboardShell mode="customer">
      <h1 className="text-3xl font-bold">Customer Dashboard</h1>
      <div className="mt-6 grid gap-5 md:grid-cols-4">
        {["Purchased Products", "Active Licenses", "Devices", "Open Tickets"].map((label) => (
          <div key={label} className="rounded-md border border-slate-200 bg-white p-5">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-2 text-3xl font-bold">0</div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
