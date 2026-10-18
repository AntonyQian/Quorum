/** "You saved $X vs list price": list price minus net paid, over orders that were paid for. */
export function totalSavingsCents(
  orders: { product: { list_price_cents: number }; net_paid_cents: number }[],
): number {
  return orders
    .filter((order) => order.net_paid_cents > 0)
    .reduce(
      (sum, order) => sum + Math.max(order.product.list_price_cents - order.net_paid_cents, 0),
      0,
    );
}
