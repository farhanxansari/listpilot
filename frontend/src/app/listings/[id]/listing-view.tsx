"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Header from "@/components/header";
import InspectionMap from "@/components/inspection-map";
import {
  API_URL,
  FINAL_STATUSES,
  type Flag,
  formatINR,
  getListing,
  type Listing,
  type ListingResponse,
  titleCase,
} from "@/lib/api";

type StreamEvent = { type: string; data: Record<string, any> }; // eslint-disable-line @typescript-eslint/no-explicit-any
type StepState = "done" | "warn" | "active" | "pending" | "failed";
type Step = { label: string; detail?: string; state: StepState };

const EVENT_TYPES = ["step", "photo_checks", "verification", "tool", "done", "error"];

const toolResults = (events: StreamEvent[], tool: string) =>
  events.filter((e) => e.type === "tool" && e.data.tool === tool).map((e) => e.data.result ?? {});

/** Turn the raw event stream into the five user-facing steps. */
function buildSteps(events: StreamEvent[], running: boolean): Step[] {
  const photo = events.find((e) => e.type === "photo_checks")?.data;
  const verification = events.find((e) => e.type === "verification")?.data;
  const reg = toolResults(events, "validate_registration").at(-1);
  const odo = toolResults(events, "check_mileage").at(-1);
  const price = toolResults(events, "estimate_price").at(-1);
  const submits = toolResults(events, "submit_listing");
  const accepted = submits.some((s) => s.accepted);
  const rejected = submits.filter((s) => s.accepted === false).length;

  const steps: (Step | null)[] = [
    photo
      ? {
          label: "Read the photos",
          detail: `${titleCase(photo.colour)} ${photo.body_type} · ${
            photo.damages.length ? `${photo.damages.length} damage found` : "no damage seen"
          }`,
          state: photo.damages.length ? "warn" : "done",
        }
      : null,
    verification
      ? {
          label: "Compared with your details",
          detail: verification.flags.length
            ? `${verification.flags.length} difference(s): ${verification.flags.map((f: Flag) => f.check).join(", ")}`
            : "Everything matches",
          state: verification.flags.length ? "warn" : "done",
        }
      : null,
    reg && odo
      ? {
          label: "Registration & mileage",
          detail: `${reg.valid ? reg.state ?? reg.series : "invalid registration"} · ${
            odo.km_per_year?.toLocaleString("en-IN")
          } km/yr, ${String(odo.verdict).replace("_", " ")}`,
          state: reg.valid && odo.verdict === "normal" ? "done" : "warn",
        }
      : null,
    price
      ? price.error
        ? { label: "Price", detail: "Not in pricing data — a human will price it", state: "warn" }
        : { label: "Priced against the Indian market", detail: `${formatINR(price.low)} – ${formatINR(price.high)}`, state: "done" }
      : null,
    accepted
      ? {
          label: "Wrote the listing",
          detail: rejected ? `Guardrails rejected ${rejected} draft(s) first` : "Passed guardrails first time",
          state: rejected ? "warn" : "done",
        }
      : null,
  ];

  const labels = ["Read the photos", "Compare with your details", "Registration & mileage", "Price against the Indian market", "Write the listing"];
  const failed = events.some((e) => e.type === "error");
  let activeSet = false;
  return steps.map((s, i) => {
    if (s) return s;
    if (!activeSet && (running || failed)) {
      activeSet = true;
      return {
        label: labels[i],
        detail: i === 4 && rejected ? `Draft ${rejected} rejected — rewriting` : undefined,
        state: failed ? "failed" : "active",
      };
    }
    return { label: labels[i], state: "pending" };
  });
}

function StepIcon({ state }: { state: StepState }) {
  const base = "flex h-[26px] w-[26px] flex-none items-center justify-center rounded-full text-[13px] font-extrabold";
  if (state === "done") return <span className={`${base} bg-green-100 text-green-800`}>✓</span>;
  if (state === "warn") return <span className={`${base} bg-amber-100 text-amber-800`}>!</span>;
  if (state === "failed") return <span className={`${base} bg-red-100 text-red-800`}>×</span>;
  if (state === "active") return <span className={`${base} animate-pulse border-[3px] border-accent`} />;
  return <span className={`${base} border-2 border-dashed border-[#9AA3AF]`} />;
}

export default function ListingView({ id }: { id: string }) {
  const [listing, setListing] = useState<ListingResponse | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [startedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    getListing(id).then(setListing).catch((e) => setLoadError(String(e)));
    const source = new EventSource(`${API_URL}/listings/${id}/stream`);
    const refresh = () => getListing(id).then(setListing).catch((e) => setLoadError(String(e)));
    const handlers = EVENT_TYPES.map((type) => {
      const handler = (e: Event) => {
        const data = (e as MessageEvent).data;
        if (data === undefined) {
          // connection dropped, not a server event: show whatever state the job is in
          source.close();
          refresh();
          return;
        }
        setEvents((prev) => [...prev, { type, data: JSON.parse(data) }]);
        if (type === "done" || type === "error") {
          source.close();
          refresh();
        }
      };
      source.addEventListener(type, handler);
      return [type, handler] as const;
    });
    return () => {
      handlers.forEach(([type, h]) => source.removeEventListener(type, h));
      source.close();
    };
  }, [id]);

  const finished = listing !== null && FINAL_STATUSES.includes(listing.status);
  useEffect(() => {
    if (finished) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [finished]);

  if (loadError && !listing) {
    return (
      <>
        <Header step={2} />
        <p role="alert" className="mx-auto mt-10 max-w-xl rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">
          Couldn&apos;t load this listing: {loadError}
        </p>
      </>
    );
  }
  if (!listing) {
    return (
      <>
        <Header step={2} />
        <p className="mx-auto mt-10 max-w-xl text-sm text-muted">Loading…</p>
      </>
    );
  }

  const steps = buildSteps(events, !finished);
  return finished && listing.status !== "failed" && listing.result ? (
    <ResultView listing={listing} events={events} steps={steps} />
  ) : (
    <LiveView listing={listing} events={events} steps={steps} elapsed={Math.round((now - startedAt) / 1000)} />
  );
}

function carName(l: ListingResponse) {
  return `${l.seller.year} ${l.seller.make} ${l.seller.model}`;
}

function LiveView({ listing, events, steps, elapsed }: {
  listing: ListingResponse; events: StreamEvent[]; steps: Step[]; elapsed: number;
}) {
  const failed = listing.status === "failed" || events.some((e) => e.type === "error");
  const photo = events.find((e) => e.type === "photo_checks")?.data;
  const doneCount = steps.filter((s) => s.state === "done" || s.state === "warn").length;
  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <>
      <Header step={2} />
      <main className="mx-auto flex max-w-[1180px] flex-wrap items-start gap-6 px-6 pb-12 pt-8">
        <section className="flex min-w-0 flex-[1.2_1_480px] flex-col gap-4">
          <div>
            <p className="mb-1.5 text-[13px] font-bold uppercase tracking-[0.08em] text-accent">
              {failed ? "Something went wrong" : "Agent at work"}
            </p>
            <h1 className="text-[34px] font-extrabold leading-tight tracking-tight">Checking your {carName(listing)}</h1>
          </div>
          <div className="relative aspect-[4/3] overflow-hidden rounded-[20px] bg-[#CFD6DE]">
            {listing.photos[0] && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`${API_URL}${listing.photos[0]}`} alt="Your car" className="h-full w-full object-cover" />
            )}
            {!failed && <div className="lp-scan absolute inset-x-0 h-[3px] bg-accent shadow-[0_0_18px_#C2410C]" />}
            {photo?.damages?.map((d: { type: string; confidence: number }, i: number) => (
              <span key={i} className="absolute left-4 rounded-md bg-red-700 px-2 py-1 text-xs font-bold text-white" style={{ top: 16 + i * 32 }}>
                {titleCase(d.type)} · {Math.round(d.confidence * 100)}%
              </span>
            ))}
          </div>
          <p className="text-sm text-muted">
            You can leave this page — the agent keeps working and the result will be here when you come back.
          </p>
        </section>

        <section aria-live="polite" className="flex min-w-0 flex-[1_1_400px] flex-col gap-4 rounded-[20px] border border-line bg-white p-6">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-bold">Live progress</h2>
            <span className="font-mono text-[13px] text-muted">{mmss}</span>
          </div>
          <ol className="flex flex-col gap-3.5">
            {steps.map((s) => (
              <li key={s.label} className={`flex items-start gap-3 ${s.state === "pending" ? "opacity-45" : ""}`}>
                <StepIcon state={s.state} />
                <div>
                  <p className="text-[15px] font-bold">{s.label}{s.state === "active" ? "…" : ""}</p>
                  {s.detail && (
                    <p className={`mt-0.5 text-[13px] ${s.state === "warn" ? "text-amber-800" : "text-muted"}`}>{s.detail}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
          <div className="h-2 rounded-full bg-[#EEF1F4]">
            <div className="h-2 rounded-full bg-accent transition-all" style={{ width: `${(doneCount / steps.length) * 100}%` }} />
          </div>
          {failed && (
            <div role="alert" className="flex flex-col gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800">
              {listing.error ?? events.find((e) => e.type === "error")?.data.message ?? "The agent stopped."}
              <Link href="/" className="font-semibold">Try again</Link>
            </div>
          )}
        </section>
      </main>
    </>
  );
}

const BANNERS: Record<string, { box: string; title: string; text: string; pill: string }> = {
  needs_review: {
    box: "border-amber-300 bg-amber-50 text-amber-900",
    title: "Needs a quick review before publishing",
    text: "The photos don't fully match what was declared. The agent explains why below.",
    pill: "bg-amber-200 text-amber-900",
  },
  ready_to_publish: {
    box: "border-green-300 bg-green-50 text-green-900",
    title: "Ready to publish",
    text: "Everything you declared matches the photos.",
    pill: "bg-green-200 text-green-900",
  },
};

function ResultView({ listing, events, steps }: { listing: ListingResponse; events: StreamEvent[]; steps: Step[] }) {
  const result = listing.result!;
  const { seller, declared_body_type: declaredBody } = listing;
  const checks = result.photo_checks;
  const banner = BANNERS[listing.status] ?? BANNERS.needs_review;
  const flagged = (check: string) => result.flags.find((f) => f.check === check);
  const reg = toolResults(events, "validate_registration").at(-1);
  const otherFlags = result.flags.filter((f) => f.by !== "verify");

  const subtitle = [seller.fuel_type, seller.transmission_type, `${seller.km_driven.toLocaleString("en-IN")} km`, reg?.state]
    .filter(Boolean)
    .join(" · ");
  const price = result.price;
  const markerPct = price ? ((price.mid - price.low) / Math.max(price.high - price.low, 1)) * 100 : 0;
  const maxDamageConf = Math.max(0, ...checks.damages.map((d) => d.confidence));

  const rows = [
    {
      field: "Body",
      said: declaredBody ? `${titleCase(declaredBody)} (${seller.model})` : seller.model,
      seen: titleCase(checks.body_type),
      conf: checks.confidence?.body_type,
      flag: flagged("body_type"),
    },
    {
      field: "Colour",
      said: seller.colour ? titleCase(seller.colour) : "Not given",
      seen: titleCase(checks.colour),
      conf: checks.confidence?.colour,
      flag: flagged("colour"),
    },
    {
      field: "Damage",
      said: seller.reported_damage === false ? "None" : seller.reported_damage ? "Some" : "Not given",
      seen: checks.damages.length
        ? checks.damages.map((d) => `${titleCase(d.type)} (${titleCase(d.location)})`).join(", ")
        : "None seen",
      conf: checks.damages.length ? maxDamageConf : undefined,
      flag: flagged("damage"),
    },
  ];

  // agent decisions, in order, from the stream
  const timeline: { text: string; tone: "ink" | "warn" | "ok"; quote?: string }[] = [];
  const stepRegOdo = steps[2];
  if (stepRegOdo.detail) timeline.push({ text: `Checked registration and mileage: ${stepRegOdo.detail}`, tone: "ink" });
  if (steps[3].detail) timeline.push({ text: `${steps[3].label}: ${steps[3].detail}`, tone: "ink" });
  let draft = 0;
  for (const e of events) {
    if (e.type !== "tool") continue;
    if (e.data.tool === "flag_for_inspection") {
      timeline.push({ text: "Flagged for a human", tone: "warn", quote: JSON.parse(e.data.args ?? "{}").reason });
    }
    if (e.data.tool === "submit_listing") {
      if (timeline.some((t) => t.tone === "ok")) continue; // ignore duplicate submits after acceptance
      draft += 1;
      const r = e.data.result ?? {};
      if (r.accepted) timeline.push({ text: `Draft ${draft} accepted`, tone: "ok" });
      else if (r.issues) timeline.push({ text: `Draft ${draft} rejected by guardrails`, tone: "warn", quote: r.issues.join(" ") });
    }
  }

  return (
    <>
      <Header step={3} />
      <main className="mx-auto flex max-w-[1180px] flex-col gap-6 px-6 pb-12 pt-8">
        <div className={`flex flex-wrap items-center justify-between gap-4 rounded-2xl border px-5 py-4 ${banner.box}`}>
          <div>
            <p className="font-bold">{banner.title}</p>
            <p className="mt-0.5 text-sm opacity-90">{banner.text}</p>
          </div>
          <span className={`rounded-full px-3 py-1.5 text-[13px] font-bold ${banner.pill}`}>
            {listing.status.replaceAll("_", " ").toUpperCase()}
          </span>
        </div>

        <div className="flex flex-wrap items-start gap-6">
          <div className="flex min-w-0 flex-[1.35_1_520px] flex-col gap-6">
            <section className="overflow-hidden rounded-[20px] border border-line bg-white">
              <div className="aspect-[16/7] bg-[#CFD6DE]">
                {listing.photos[0] && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={`${API_URL}${listing.photos[0]}`} alt={carName(listing)} className="h-full w-full object-cover" />
                )}
              </div>
              <div className="flex flex-col gap-5 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h1 className="text-3xl font-extrabold tracking-tight">{carName(listing)}</h1>
                    <p className="mt-1.5 text-[15px] text-muted">{subtitle}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[13px] font-semibold text-muted">Estimated price</p>
                    <p className="mt-0.5 text-4xl font-extrabold tracking-tight">{price ? formatINR(price.mid) : "—"}</p>
                  </div>
                </div>
                {price ? (
                  <div className="flex flex-col gap-2">
                    <div className="relative h-3 rounded-full bg-gradient-to-r from-accent-tint to-accent-soft">
                      <div className="absolute -top-1.5 h-6 w-1 rounded-sm bg-ink" style={{ left: `calc(${markerPct}% - 2px)` }} />
                    </div>
                    <div className="flex justify-between text-[13px] text-muted">
                      <span><strong className="text-ink">{formatINR(price.low)}</strong> low</span>
                      <span className="hidden sm:inline">80% of similar cars sell in this range</span>
                      <span>high <strong className="text-ink">{formatINR(price.high)}</strong></span>
                    </div>
                  </div>
                ) : (
                  <p className="rounded-xl bg-amber-50 px-3.5 py-2.5 text-sm text-amber-900">
                    This model isn&apos;t in the pricing data yet, so a human will set the price.
                  </p>
                )}
              </div>
            </section>

            <section className="flex flex-col gap-3.5 rounded-[20px] border border-line bg-white p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-lg font-bold">Inspection map</h2>
                <span className={`text-sm font-semibold ${checks.damages.length ? "text-red-700" : "text-green-800"}`}>
                  {checks.damages.length ? `${checks.damages.length} issue(s) found in photos` : "No damage found in photos"}
                </span>
              </div>
              <InspectionMap damages={checks.damages} />
              {checks.damages.map((d, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl bg-red-50 px-3.5 py-3">
                  <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-red-700 text-[13px] font-extrabold text-white">{i + 1}</span>
                  <span className="text-sm leading-relaxed text-red-900">
                    <strong>{titleCase(d.location)} · {d.type.replaceAll("_", " ")}</strong> — {d.description}. Seen with{" "}
                    {Math.round(d.confidence * 100)}% confidence.
                  </span>
                </div>
              ))}
              {checks.notes && <p className="text-[13px] text-muted">Photo notes: {checks.notes}</p>}
            </section>

            {result.listing && <ListingEditor initial={result.listing} />}
          </div>

          <aside className="flex min-w-0 flex-[1_1_380px] flex-col gap-5">
            <section className="overflow-hidden rounded-[20px] border border-line bg-white">
              <div className="px-5 pb-3 pt-5">
                <h2 className="text-lg font-bold">You said vs photos show</h2>
                <p className="mt-1 text-[13px] text-muted">The agent checks every claim against the photos.</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="text-left text-xs text-muted">
                      <th className="px-5 py-2 font-semibold"><span className="sr-only">Field</span></th>
                      <th className="px-2 py-2 font-semibold">You said</th>
                      <th className="py-2 pl-2 pr-5 font-semibold">Photos show</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => {
                      const high = r.flag?.severity === "high";
                      return (
                        <tr key={r.field} className={`border-t border-[#EEF1F4] ${high ? "bg-red-50" : ""}`}>
                          <td className="px-5 py-3 font-semibold">{r.field}</td>
                          <td className="px-2 py-3">{r.said}</td>
                          <td className="py-3 pl-2 pr-5">
                            <div className={`flex items-center gap-2 ${high ? "font-bold text-red-800" : ""}`}>
                              <span className={`font-extrabold ${r.flag ? (high ? "text-red-700" : "text-amber-700") : "text-green-800"}`}>
                                {r.flag ? "≠" : "✓"}
                              </span>
                              {r.seen}
                            </div>
                            {r.conf !== undefined && (
                              <>
                                <div className={`mt-1.5 h-1 rounded-sm ${high ? "bg-red-200" : "bg-[#EEF1F4]"}`}>
                                  <div className={`h-1 rounded-sm ${high ? "bg-red-700" : "bg-ink"}`} style={{ width: `${Math.round(r.conf * 100)}%` }} />
                                </div>
                                <span className="font-mono text-[11px] text-muted">{Math.round(r.conf * 100)}% sure</span>
                              </>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="flex flex-col gap-3 rounded-[20px] border border-line bg-white p-5">
              <h2 className="text-lg font-bold">How the agent wrote it</h2>
              <ol className="flex flex-col">
                {timeline.map((t, i) => (
                  <li key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className={`mt-1 h-3 w-3 rounded-full ${t.tone === "warn" ? "bg-amber-700" : t.tone === "ok" ? "bg-green-800" : "bg-ink"}`} />
                      {i < timeline.length - 1 && <span className="w-0.5 flex-1 bg-line" />}
                    </div>
                    <div className="flex flex-col gap-1.5 pb-3.5 text-sm leading-relaxed">
                      <span className={t.tone === "ink" ? "" : "font-bold"}>{t.text}</span>
                      {t.quote && (
                        <span className="rounded-[10px] border border-amber-200 bg-amber-50 px-2.5 py-2 text-[13px] text-amber-900">
                          &ldquo;{t.quote}&rdquo;
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
              {otherFlags.length > 0 && (
                <ul className="flex flex-col gap-2">
                  {otherFlags.map((f, i) => (
                    <li key={i} className="flex gap-2 rounded-xl bg-amber-50 px-3 py-2 text-[13px] text-amber-900">
                      <span className="font-extrabold uppercase">{f.severity}</span>
                      {f.reason}
                    </li>
                  ))}
                </ul>
              )}
              <p className="font-mono text-xs text-muted">
                {result.metrics.latency_s}s · {result.metrics.tokens.toLocaleString("en-IN")} tokens ·{" "}
                {result.metrics.agent_steps} agent steps
              </p>
            </section>

            <PublishButtons status={listing.status} />
          </aside>
        </div>
      </main>
    </>
  );
}

function PublishButtons({ status }: { status: string }) {
  const [approved, setApproved] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setApproved(true)}
        disabled={approved}
        className="h-14 rounded-[14px] bg-accent font-bold text-white hover:bg-accent-dark disabled:bg-green-800"
      >
        {approved ? "Published ✓" : status === "needs_review" ? "I've reviewed it — publish" : "Publish"}
      </button>
      <Link
        href="/"
        className="flex h-12 items-center justify-center rounded-[14px] border border-field bg-white font-semibold text-ink hover:border-ink"
      >
        Fix my details
      </Link>
    </>
  );
}

function ListingEditor({ initial }: { initial: Listing }) {
  const [title, setTitle] = useState(initial.title);
  const [description, setDescription] = useState(initial.description);
  const [highlights, setHighlights] = useState(initial.highlights.join("\n"));
  const edited = [
    title !== initial.title,
    description !== initial.description,
    highlights !== initial.highlights.join("\n"),
  ].filter(Boolean).length;
  const box =
    "w-full rounded-xl border border-field px-3.5 font-medium text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent-tint";

  return (
    <section className="flex flex-col gap-3 rounded-[20px] border border-line bg-white p-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-bold">Listing draft</h2>
        <span className="text-[13px] text-muted">{edited ? `${edited} field(s) edited` : "Written by the agent · edit anything"}</span>
      </div>
      <label className="flex flex-col gap-1.5 text-[13px] font-bold text-muted">
        TITLE
        <input className={`${box} h-12 text-base font-semibold`} value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label className="flex flex-col gap-1.5 text-[13px] font-bold text-muted">
        DESCRIPTION
        <textarea rows={3} className={`${box} py-3 text-[15px] leading-relaxed`} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="flex flex-col gap-1.5 text-[13px] font-bold text-muted">
        HIGHLIGHTS · one per line
        <textarea rows={4} className={`${box} py-3 text-[15px] leading-relaxed`} value={highlights} onChange={(e) => setHighlights(e.target.value)} />
      </label>
    </section>
  );
}