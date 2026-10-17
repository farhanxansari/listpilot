export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Seller = {
  registration_number: string;
  make: string;
  model: string;
  year: number;
  km_driven: number;
  fuel_type: string;
  transmission_type: string;
  colour: string | null;
  reported_damage: boolean | null;
  seller_notes: string | null;
};

export type Flag = { reason: string; severity: "low" | "high"; by: string; check?: string };
export type Damage = { type: string; location: string; description: string; confidence: number };
export type Price = { matched: string; low: number; mid: number; high: number; note: string };
export type Listing = { title: string; description: string; highlights: string[] };

export type PhotoChecks = {
  body_type: string;
  colour: string;
  damages: Damage[];
  notes: string | null;
  confidence?: { body_type: number; colour: number };
};

export type Result = {
  status: string;
  listing: Listing | null;
  price: Price | null;
  flags: Flag[];
  photo_checks: PhotoChecks;
  metrics: { latency_s: number; tokens: number; agent_steps: number };
};

export type ListingResponse = {
  id: string;
  status: string;
  seller: Seller;
  declared_body_type: string | null;
  photos: string[];
  result: Result | null;
  error: string | null;
};

export type Catalog = { makes: { make: string; models: string[] }[] };

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function getCatalog(): Promise<Catalog> {
  return asJson(await fetch(`${API_URL}/catalog`));
}

export async function createListing(photos: File[], seller: Seller): Promise<{ id: string }> {
  const form = new FormData();
  photos.forEach((p) => form.append("photos", p));
  form.append("seller", JSON.stringify(seller));
  return asJson(await fetch(`${API_URL}/listings`, { method: "POST", body: form }));
}

export async function getListing(id: string): Promise<ListingResponse> {
  return asJson(await fetch(`${API_URL}/listings/${id}`));
}

export const formatINR = (n: number) =>
  n >= 100000 ? `₹${(n / 100000).toFixed(2)} L` : `₹${n.toLocaleString("en-IN")}`;

export const FINAL_STATUSES = ["ready_to_publish", "needs_review", "failed"];

export const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replaceAll("_", " ");