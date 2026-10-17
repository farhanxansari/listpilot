import { Suspense } from "react";

import ListingView from "./listing-view";

// The id is only known at request time, so read it inside a Suspense boundary.
export default function ListingPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-stone-500">Loading…</p>}>
      <WithId params={params} />
    </Suspense>
  );
}

async function WithId({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ListingView id={id} />;
}