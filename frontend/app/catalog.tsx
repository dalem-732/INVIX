"use client";

import { useEffect, useState } from "react";
import { ProductCard } from "./product-card";
import { ProductDialog } from "./product-dialog";
import type { Product } from "./types";
import { XpWindow } from "./xp-window";

export type { Product };

export function Catalog({
  products,
  loadError = false,
}: {
  products: Product[];
  loadError?: boolean;
}) {
  const [opened, setOpened] = useState<Product | null>(null);

  useEffect(() => {
    if (!opened) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpened(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [opened]);

  const status = loadError ? "Ошибка загрузки" : `Объектов: ${products.length}`;

  return (
    <>
      <XpWindow title="Каталог" heading className="catalog" status={status}>
        {loadError ? (
          <p>Не удалось загрузить каталог.</p>
        ) : (
          <ul className="products">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} onOpen={setOpened} />
            ))}
          </ul>
        )}
      </XpWindow>
      {opened ? <ProductDialog product={opened} onClose={() => setOpened(null)} /> : null}
    </>
  );
}
