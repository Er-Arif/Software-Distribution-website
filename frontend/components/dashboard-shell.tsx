import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { BarChart3, Boxes, CreditCard, Download, KeyRound, LifeBuoy, Settings, Users } from "lucide-react";

type NavItem = [label: string, href: string, Icon: LucideIcon];

const customerNav: NavItem[] = [
  ["Dashboard", "/dashboard", BarChart3],
  ["My Products", "/dashboard/products", Boxes],
  ["Downloads", "/dashboard/downloads", Download],
  ["Licenses", "/dashboard/licenses", KeyRound],
  ["Billing", "/dashboard/billing", CreditCard],
  ["Support", "/dashboard/support", LifeBuoy]
];

const adminNav: NavItem[] = [
  ["Dashboard", "/admin", BarChart3],
  ["Products", "/admin/products", Boxes],
  ["Customers", "/admin/customers", Users],
  ["Licenses", "/admin/licenses", KeyRound],
  ["Downloads", "/admin/downloads", Download],
  ["Analytics", "/admin/analytics", BarChart3],
  ["Settings", "/admin/settings", Settings]
];

export function DashboardShell({ children, mode }: { children: React.ReactNode; mode: "customer" | "admin" }) {
  const nav = mode === "admin" ? adminNav : customerNav;
  return (
    <div className="min-h-screen bg-paper">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white p-5 md:block">
        <Link href="/" className="text-lg font-semibold text-ink">
          Software Store
        </Link>
        <nav className="mt-8 space-y-1">
          {nav.map(([label, href, Icon]) => (
            <Link key={href} href={href} className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="md:pl-64">
        <div className="mx-auto max-w-7xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
