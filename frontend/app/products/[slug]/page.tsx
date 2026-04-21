import { ButtonLink, Shell, StatusBadge } from "@/components/ui";
import { apiGet, Product } from "@/lib/api";

type ProductDetail = { product: Product; plans: Array<{ id: string; name: string; code: string; price_amount: number; currency: string; billing_interval: string }> };

export default async function ProductDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = await apiGet<ProductDetail>(`/public/products/${slug}`).catch(() => null);
  return (
    <Shell>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <StatusBadge>{data?.product.supported_os.join(" / ") ?? "Desktop app"}</StatusBadge>
        <h1 className="mt-4 text-4xl font-bold">{data?.product.name ?? "Product"}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">{data?.product.short_description ?? "Product details load from the platform API."}</p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {(data?.plans ?? []).map((plan) => (
            <div key={plan.id} className="rounded-md border border-slate-200 bg-white p-5">
              <div className="font-semibold">{plan.name}</div>
              <div className="mt-3 text-3xl font-bold">
                {plan.currency} {plan.price_amount}
              </div>
              <p className="mt-2 text-sm text-slate-600">Includes signed updates, protected downloads, and license validation.</p>
              <div className="mt-5">
                <ButtonLink href={`/checkout?plan=${plan.code}`}>Buy now</ButtonLink>
              </div>
            </div>
          ))}
        </div>
      </section>
    </Shell>
  );
}
