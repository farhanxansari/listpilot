"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import Header from "@/components/header";
import { type Catalog, createListing, getCatalog } from "@/lib/api";

const MAX_PHOTOS = 6;
const THIS_YEAR = new Date().getFullYear();
const SUGGESTED_ANGLES = ["Front ¾", "Side", "Rear"];
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const FUELS = ["Petrol", "Diesel", "CNG", "LPG", "Electric"];
const TRANSMISSIONS = ["Manual", "Automatic"];
const SWATCHES: [string, string][] = [
  ["white", "#FFFFFF"], ["silver", "#C8CDD3"], ["grey", "#6B7280"], ["black", "#111827"],
  ["red", "#B91C1C"], ["blue", "#1D4ED8"], ["brown", "#78350F"], ["beige", "#D6C4A0"],
  ["green", "#15803D"], ["yellow", "#EAB308"], ["orange", "#EA580C"],
];
const DAMAGE_CHOICES = [
  ["none", "No damage"],
  ["some", "Yes, some"],
  ["unknown", "Not sure"],
] as const;
type DamageChoice = (typeof DAMAGE_CHOICES)[number][0];

const fieldCls =
  "h-12 w-full rounded-xl border border-field bg-white px-3 font-medium text-ink " +
  "focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent-tint";

function Chip({ active, onClick, children, wide = false }: {
  active: boolean; onClick: () => void; children: React.ReactNode; wide?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`h-11 px-4 font-semibold ${wide ? "flex-1 rounded-xl" : "rounded-full"} ${
        active ? "border-2 border-ink bg-ink text-white" : "border border-field bg-white text-ink hover:border-ink"
      }`}
    >
      {children}
    </button>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <span className="text-sm font-semibold">{children}</span>;
}

export default function NewListingPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState(2019);
  const [km, setKm] = useState(40000);
  const [fuel, setFuel] = useState("Petrol");
  const [transmission, setTransmission] = useState("Manual");
  const [colour, setColour] = useState<string | null>(null);
  const [registration, setRegistration] = useState("");
  const [damage, setDamage] = useState<DamageChoice>("unknown");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCatalog()
      .then(setCatalog)
      .catch(() => setCatalogError("Can't reach the API. Is the backend running on port 8000?"));
  }, []);

  const models = useMemo(
    () => catalog?.makes.find((m) => m.make === make)?.models ?? [],
    [catalog, make],
  );

  // revoke preview URLs when photos change, so they don't leak memory
  const previews = useMemo(() => photos.map((p) => URL.createObjectURL(p)), [photos]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  // A drop that misses the drop zone would make the browser open the image and leave the form.
  useEffect(() => {
    const block = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", block);
    window.addEventListener("drop", block);
    return () => {
      window.removeEventListener("dragover", block);
      window.removeEventListener("drop", block);
    };
  }, []);

  function addPhotos(files: FileList | null) {
    if (!files) return;
    // copy now: the input is cleared right after, which empties the live FileList
    const all = Array.from(files);
    const picked = all.filter((f) => ACCEPTED_TYPES.includes(f.type));
    if (picked.length < all.length) {
      setError("Only JPEG, PNG or WebP photos can be added (drag the file itself, not a browser image).");
    } else {
      setError(null);
    }
    setPhotos((prev) => [...prev, ...picked].slice(0, MAX_PHOTOS));
  }

  // The whole Photos card is the drop target. A counter keeps the highlight steady while
  // the pointer moves over child elements (each fires its own dragenter/dragleave).
  const dropProps = {
    onDragEnter: (e: React.DragEvent) => {
      e.preventDefault();
      dragDepth.current += 1;
      setDragging(true);
    },
    onDragOver: (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    },
    onDragLeave: () => {
      dragDepth.current = Math.max(0, dragDepth.current - 1);
      if (dragDepth.current === 0) setDragging(false);
    },
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      dragDepth.current = 0;
      setDragging(false);
      addPhotos(e.dataTransfer.files);
    },
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (photos.length === 0) return setError("Add at least one photo of the car.");
    setSubmitting(true);
    try {
      const { id } = await createListing(photos, {
        registration_number: registration,
        make,
        model,
        year,
        km_driven: km,
        fuel_type: fuel,
        transmission_type: transmission,
        colour,
        reported_damage: damage === "unknown" ? null : damage === "some",
        seller_notes: notes || null,
      });
      router.push(`/listings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <>
      <Header step={1} />
      <form onSubmit={submit} className="mx-auto flex max-w-[1180px] flex-col gap-7 px-6 pb-12 pt-10">
        <div>
          <p className="mb-2 text-[13px] font-bold uppercase tracking-[0.08em] text-accent">Sell your car</p>
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-[44px]">
            List it in a minute.
            <br />
            We check it in thirty seconds.
          </h1>
          <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
            Tell us what you&apos;re selling and add photos. ListPilot checks the photos against your
            details, prices the car and writes the listing.
          </p>
        </div>

        {catalogError && (
          <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{catalogError}</p>
        )}

        <div className="flex flex-wrap items-start gap-6">
          <section
            {...dropProps}
            className={`flex min-w-0 flex-[1_1_420px] flex-col gap-4 rounded-[20px] border bg-white p-6 ${
              dragging ? "border-accent ring-4 ring-accent-tint" : "border-line"
            }`}
          >
            <div className="flex items-baseline justify-between">
              <h2 className="text-lg font-bold">Photos</h2>
              <span className="text-sm text-muted">{photos.length} of {MAX_PHOTOS}</span>
            </div>
            {photos.length < MAX_PHOTOS && (
              <label
                className={`flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-4 py-9 text-center hover:border-accent ${
                  dragging ? "border-accent bg-orange-50" : "border-field bg-[#FAFBFC]"
                }`}
              >
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#5B6675" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 16V4M7 9l5-5 5 5" />
                  <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
                </svg>
                <span className="font-bold">Drop photos or browse</span>
                <span className="text-sm text-muted">Front, side, rear — and close-ups of any damage</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  className="sr-only"
                  onChange={(e) => {
                    addPhotos(e.target.files);
                    e.target.value = "";
                  }}
                />
              </label>
            )}
            <div className="grid grid-cols-3 gap-3">
                {previews.map((src, i) => (
                  <div key={src} className="relative aspect-[4/3] overflow-hidden rounded-xl bg-[#D9DEE5]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={src} alt={`Photo ${i + 1}`} className="h-full w-full object-cover" />
                    <button
                      type="button"
                      onClick={() => setPhotos((p) => p.filter((_, j) => j !== i))}
                      aria-label={`Remove photo ${i + 1}`}
                      className="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-full bg-ink/75 text-sm text-white"
                    >
                      ×
                    </button>
                  </div>
                ))}
                {/* suggested angles still missing, so sellers know what to shoot next */}
                {SUGGESTED_ANGLES.slice(photos.length).map((angle) => (
                  <div
                    key={angle}
                    className="flex aspect-[4/3] items-center justify-center rounded-xl border border-dashed border-field text-[13px] text-muted"
                  >
                    + {angle}
                  </div>
                ))}
              </div>
            <p className="flex gap-2.5 rounded-xl bg-orange-50 px-3.5 py-3 text-sm leading-relaxed text-orange-900">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C2410C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mt-0.5 flex-none">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8v5M12 16h.01" />
              </svg>
              Number plates are fine — they are never shown in the public listing.
            </p>
          </section>

          <section className="grid min-w-0 flex-[1.3_1_480px] grid-cols-1 gap-4 rounded-[20px] border border-line bg-white p-6 sm:grid-cols-2">
            <h2 className="text-lg font-bold sm:col-span-2">Car details</h2>
            <label className="flex flex-col gap-1.5">
              <Label>Make</Label>
              <select required className={fieldCls} value={make} onChange={(e) => { setMake(e.target.value); setModel(""); }}>
                <option value="">Select make</option>
                {catalog?.makes.map((m) => <option key={m.make}>{m.make}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <Label>Model</Label>
              <select required disabled={!make} className={fieldCls} value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="">{make ? "Select model" : "Pick a make first"}</option>
                {models.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <Label>Year</Label>
              <input required type="number" min={1990} max={THIS_YEAR} className={fieldCls} value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </label>
            <label className="flex flex-col gap-1.5">
              <Label>Kilometres</Label>
              <input required type="number" min={0} className={fieldCls} value={km} onChange={(e) => setKm(Number(e.target.value))} />
            </label>

            <fieldset className="flex flex-col gap-1.5 sm:col-span-2">
              <legend className="mb-1.5 text-sm font-semibold">Fuel</legend>
              <div className="flex flex-wrap gap-2">
                {FUELS.map((f) => <Chip key={f} active={fuel === f} onClick={() => setFuel(f)}>{f}</Chip>)}
              </div>
            </fieldset>
            <fieldset className="flex flex-col gap-1.5">
              <legend className="mb-1.5 text-sm font-semibold">Transmission</legend>
              <div className="flex gap-2">
                {TRANSMISSIONS.map((t) => <Chip key={t} wide active={transmission === t} onClick={() => setTransmission(t)}>{t}</Chip>)}
              </div>
            </fieldset>
            <label className="flex flex-col gap-1.5">
              <Label>Registration</Label>
              <input required placeholder="e.g. DL 3C AB 1234" className={fieldCls} value={registration} onChange={(e) => setRegistration(e.target.value)} />
            </label>

            <fieldset className="flex flex-col gap-1.5 sm:col-span-2">
              <legend className="mb-1.5 text-sm font-semibold">
                Colour <span className="font-normal text-muted">{colour ? `· ${colour}` : "· optional"}</span>
              </legend>
              <div className="flex flex-wrap gap-2.5">
                {SWATCHES.map(([name, hex]) => (
                  <button
                    key={name}
                    type="button"
                    aria-label={name}
                    aria-pressed={colour === name}
                    onClick={() => setColour(colour === name ? null : name)}
                    style={{ background: hex }}
                    className={`h-11 w-11 rounded-full ${
                      colour === name ? "border-[3px] border-ink shadow-[inset_0_0_0_3px_#fff]" : "border border-field"
                    }`}
                  />
                ))}
              </div>
            </fieldset>

            <fieldset className="flex flex-col gap-1.5 sm:col-span-2">
              <legend className="mb-1.5 text-sm font-semibold">Any damage?</legend>
              <div className="flex flex-wrap gap-2">
                {DAMAGE_CHOICES.map(([value, label]) => (
                  <Chip key={value} wide active={damage === value} onClick={() => setDamage(value)}>{label}</Chip>
                ))}
              </div>
            </fieldset>

            <label className="flex flex-col gap-1.5 sm:col-span-2">
              <Label>Notes <span className="font-normal text-muted">· optional</span></Label>
              <textarea
                rows={2}
                placeholder="Service history, number of owners, recent repairs…"
                className={`${fieldCls} h-auto py-2.5`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </label>
          </section>
        </div>

        {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}

        <div className="flex flex-wrap items-center justify-between gap-4 rounded-[20px] bg-ink px-6 py-5 text-white">
          <span className="text-[15px] leading-relaxed text-[#D5DCE4]">
            Takes about 30 seconds. You review everything before it goes live.
          </span>
          <button
            type="submit"
            disabled={submitting || !catalog}
            className="h-[52px] rounded-[14px] bg-accent px-7 font-bold text-white hover:bg-accent-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Uploading…" : "Check & price my car →"}
          </button>
        </div>
        <p className="text-center text-xs text-muted">
          Model list comes from the pricing dataset (2021 Indian market), so some newer models are missing.
        </p>
      </form>
    </>
  );
}