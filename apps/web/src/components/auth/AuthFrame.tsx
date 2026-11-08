import Brand from "@/components/ui/Brand";

export default function AuthFrame({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand p-12 lg:flex">
        <Brand size="lg" />
        <div>
          <h2 className="font-serif text-4xl font-bold leading-tight text-ink">Orders from your DMs,<br />sorted before you open them.</h2>
          <ul className="mt-6 space-y-3 text-lg text-brand-dark">
            <li>The agent answers price and stock questions.</li>
            <li>Custom requests and complaints wait for you.</li>
            <li>Every order keeps its own proof trail.</li>
          </ul>
        </div>
        <p className="text-sm text-brand-dark/80">Built for sellers who run their shop from Instagram and WhatsApp.</p>
      </div>
      <div className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><Brand /></div>
          <h1 className="font-serif text-3xl font-bold">{title}</h1>
          <p className="mt-1 text-stone-600">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
