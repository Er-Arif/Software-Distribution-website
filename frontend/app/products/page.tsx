import { Shell } from "@/components/ui";
import { apiGet, Product } from "@/lib/api";

export default async function ProductsPage() {
  let products: Product[] = [];
  try {
    products = await apiGet<Product[]>("/public/products");
  } catch {}
  return (
    <Shell>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="text-3xl font-bold">Products</h1>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {products.map((product) => (
            <a key={product.id} href={`/products/${product.slug}`} className="rounded-md border border-slate-200 bg-white p-5">
              <div className="text-lg font-semibold">{product.name}</div>
              <p className="mt-2 text-sm text-slate-600">{product.short_description}</p>
            </a>
          ))}
        </div>
      </section>
    </Shell>
  );
}
