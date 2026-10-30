import { Catalog } from "./catalog";
import type { Product } from "./types";

export const dynamic = "force-dynamic";

async function loadProducts(): Promise<{ products: Product[]; loadError: boolean }> {
  const apiUrl = process.env.API_URL ?? "http://api:8000";
  try {
    const response = await fetch(`${apiUrl}/products`, { cache: "no-store" });
    if (!response.ok) return { products: [], loadError: true };
    return { products: (await response.json()) as Product[], loadError: false };
  } catch {
    return { products: [], loadError: true };
  }
}

export default async function HomePage() {
  const { products, loadError } = await loadProducts();
  return <Catalog products={products} loadError={loadError} />;
}
