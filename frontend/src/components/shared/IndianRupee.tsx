export function formatINR(amount: number | null | undefined): string {
  if (amount == null) return "₹0";
  return `₹${Math.round(amount).toLocaleString("en-IN")}`;
}

export function IndianRupee({
  amount,
  className = "",
}: {
  amount: number | null | undefined;
  className?: string;
}) {
  return <span className={`font-mono ${className}`}>{formatINR(amount)}</span>;
}
