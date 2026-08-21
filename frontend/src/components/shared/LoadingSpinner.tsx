/**
 * Skeleton placeholders. Named LoadingSpinner for import compatibility across
 * the pages — there is no spinner anywhere in the product, only shimmering
 * blocks in the shape of the content they replace.
 */
export function LoadingSpinner({
  label = "Loading",
  rows = 4,
  height = 40,
}: {
  label?: string;
  rows?: number;
  height?: number;
}) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton w-full" style={{ height }} />
      ))}
    </div>
  );
}

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} />;
}

/** Metric-card shaped skeleton, so the dashboard doesn't jump on load. */
export function MetricCardSkeleton({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="panel-card">
          <div className="skeleton h-3 w-24" />
          <div className="skeleton mt-4 h-8 w-16" />
          <div className="skeleton mt-3 h-2.5 w-20" />
        </div>
      ))}
    </>
  );
}
