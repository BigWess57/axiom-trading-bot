import { PulseFeed } from "@/components/PulseFeed";

export default function Home() {
  return (
    <main className="min-h-screen bg-dots-pattern">
      <div className="absolute inset-0 bg-linear-to-b from-slate-950/80 to-slate-950 pointer-events-none" />
      <div className="relative z-10">
        <PulseFeed />
      </div>
    </main>
  );
}
