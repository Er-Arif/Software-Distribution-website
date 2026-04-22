import { Shell } from "@/components/ui";

const features = [
  "Signed license validation responses",
  "Device activation and revocation",
  "Protected installer downloads",
  "Signed update manifests and rollback",
  "Razorpay and PayPal billing architecture",
  "Admin audit logs and domain events"
];

export default function FeaturesPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="text-3xl font-bold">Features</h1>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <div key={feature} className="rounded-md border border-slate-200 bg-white p-5 text-sm font-medium shadow-sm">
              {feature}
            </div>
          ))}
        </div>
      </section>
    </Shell>
  );
}
