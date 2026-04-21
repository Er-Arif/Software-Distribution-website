import { ButtonLink, Shell, StatusBadge } from "@/components/ui";
import { apiGet, Product } from "@/lib/api";

async function getProducts() {
  try {
    return await apiGet<Product[]>("/public/products");
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const products = await getProducts();
  return (
    <Shell>
      <section className="bg-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-6 py-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <StatusBadge>Licensing, updates, commerce</StatusBadge>
            <h1 className="mt-5 max-w-3xl text-5xl font-bold tracking-normal text-ink">
              Sell and secure your desktop software from one platform.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
              A complete software store with protected downloads, signed license validation, device activations, release channels, billing, and customer support.
            </p>
            <div className="mt-8 flex gap-3">
              <ButtonLink href="/products">Browse products</ButtonLink>
              <ButtonLink href="/pricing">View pricing</ButtonLink>
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-6">
            <div className="grid gap-4">
              {["Asymmetric signed license responses", "Short-lived protected installer links", "Rollback-ready signed update manifests", "Razorpay, UPI, PayPal billing"].map((item) => (
                <div key={item} className="rounded-md bg-white p-4 text-sm font-medium shadow-sm">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <h2 className="text-2xl font-semibold text-ink">Featured software</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {(products.length ? products : fallbackProducts).map((product) => (
            <a key={product.slug} href={`/products/${product.slug}`} className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
              <div className="text-lg font-semibold">{product.name}</div>
              <p className="mt-2 text-sm text-slate-600">{product.tagline}</p>
              <div className="mt-4 text-xs font-semibold uppercase text-brand">{product.supported_os.join(" / ")}</div>
            </a>
          ))}
        </div>
      </section>
    </Shell>
  );
}

const fallbackProducts: Product[] = [
  { id: "1", name: "CodeVault Pro", slug: "codevault-pro", tagline: "Secure developer secret vault.", short_description: "", supported_os: ["windows", "macos", "linux"], status: "published" },
  { id: "2", name: "InvoiceForge", slug: "invoiceforge", tagline: "GST-ready desktop invoicing.", short_description: "", supported_os: ["windows", "macos"], status: "published" },
  { id: "3", name: "MediaBatch Studio", slug: "mediabatch-studio", tagline: "Batch media automation.", short_description: "", supported_os: ["windows", "linux"], status: "published" }
];
