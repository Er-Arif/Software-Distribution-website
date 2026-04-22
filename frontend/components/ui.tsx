import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AuthLinks } from "@/components/auth-links";

export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white/90">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck className="h-5 w-5 text-brand" />
          Software Store
        </Link>
        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-700 md:flex">
          <Link href="/products">Products</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/changelog">Changelog</Link>
          <Link href="/help">Help</Link>
          <AuthLinks />
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-10 text-sm text-slate-600 md:grid-cols-4">
        <div>
          <div className="font-semibold text-ink">Software Store</div>
          <p className="mt-2">Secure licensing, updates, downloads, and billing for desktop software.</p>
        </div>
        <Link href="/legal/terms">Terms</Link>
        <Link href="/legal/privacy">Privacy</Link>
        <Link href="/contact">Contact</Link>
      </div>
    </footer>
  );
}

export function ButtonLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-800"
    >
      {children}
      <ArrowRight className="h-4 w-4" />
    </Link>
  );
}

export function StatusBadge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">{children}</span>;
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main>{children}</main>
      <Footer />
    </>
  );
}
