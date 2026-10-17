import Link from "next/link";

const STEPS = ["Photos & details", "Agent checks", "Review & publish"];

/** Top bar with the three-step progress. `step` is 1, 2 or 3. */
export default function Header({ step }: { step: 1 | 2 | 3 }) {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5" aria-label="ListPilot home">
          <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-accent">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 17h14M6 17l1.5-5h9L18 17M8 12l1.5-4h5L16 12" />
              <circle cx="8" cy="18" r="1.5" />
              <circle cx="16" cy="18" r="1.5" />
            </svg>
          </span>
          <span className="text-xl font-extrabold tracking-tight">ListPilot</span>
        </Link>
        <nav aria-label="Progress" className="flex flex-wrap gap-2 text-sm font-semibold">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const current = n === step;
            return (
              <span
                key={label}
                aria-current={current ? "step" : undefined}
                className={
                  current
                    ? "rounded-full bg-ink px-3.5 py-2 text-white"
                    : "rounded-full border border-line px-3.5 py-2 text-muted"
                }
              >
                {n} · {label}
                {n < step ? " ✓" : ""}
              </span>
            );
          })}
        </nav>
      </div>
    </header>
  );
}