import { Shell } from "@/components/ui";

export default async function LegalPage({ params }: { params: Promise<{ type: string }> }) {
  const { type } = await params;
  return (
    <Shell>
      <section className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-3xl font-bold capitalize">{type.replace("-", " ")}</h1>
        <p className="mt-3 text-slate-600">Legal content is versioned and managed from the admin panel.</p>
      </section>
    </Shell>
  );
}
