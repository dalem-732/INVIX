import type { Product } from "./types";

export function ProductCard({
  product,
  onOpen,
}: {
  product: Product;
  onOpen: (product: Product) => void;
}) {
  return (
    <li>
      <button type="button" className="product" onClick={() => onOpen(product)}>
        <img src={product.image_url} alt="" />
        <span>{product.name}</span>
      </button>
    </li>
  );
}
