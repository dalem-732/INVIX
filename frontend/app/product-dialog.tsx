import type { Product } from "./types";
import { XpWindow } from "./xp-window";

export function ProductDialog({
  product,
  onClose,
}: {
  product: Product;
  onClose: () => void;
}) {
  return (
    <div className="backdrop" onClick={onClose}>
      <XpWindow
        root="div"
        className="dialog"
        title={product.name}
        titleId="product-title"
        role="dialog"
        ariaModal
        ariaLabelledBy="product-title"
        onClick={(event) => event.stopPropagation()}
        controls={
          <button type="button" aria-label="Close" onClick={onClose} />
        }
      >
        <img className="preview" src={product.image_url} alt={product.name} />
        <p>{product.name}</p>
        <div className="dialog-actions">
          <button type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </XpWindow>
    </div>
  );
}
