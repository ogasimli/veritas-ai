import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold">Veritas AI</h1>
      <p className="mt-4 text-xl">Multi-agent AI co-auditor</p>
      <div className="mt-8">
        <Button>Get Started</Button>
      </div>
    </main>
  );
}
