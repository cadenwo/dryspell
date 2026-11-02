import Dashboard from "@/components/Dashboard";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <header className="mb-10">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">PNW granite · bouldering</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Dryspell</h1>
        <p className="mt-3 max-w-2xl text-muted">
          When will the rock be dry? A physics-based moisture model, driven by hourly rain and FAO-56
          evapotranspiration from Open-Meteo, estimates how wet each area is now and when the next
          climbable window opens.
        </p>
      </header>

      <Dashboard />

      <footer className="mt-14 border-t border-line pt-6 text-xs leading-relaxed text-muted">
        <p>
          Estimates only. Always check the rock yourself, and avoid climbing wet rock. Weather data:{" "}
          <a className="underline underline-offset-2" href="https://open-meteo.com/" target="_blank" rel="noreferrer">
            Open-Meteo
          </a>{" "}
          (CC BY 4.0).
        </p>
      </footer>
    </main>
  );
}
