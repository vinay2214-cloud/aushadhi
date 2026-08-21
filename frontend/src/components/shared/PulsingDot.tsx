type DotColor = "green" | "red" | "amber" | "orange" | "slate";

const COLORS: Record<DotColor, string> = {
  green: "#22C55E",
  red: "#EF4444",
  amber: "#F59E0B",
  orange: "#F97316",
  slate: "#52525B",
};

/**
 * Status dot. Static by default — the only animated dot in the product is the
 * outbreak banner's, which opts in with `pulse` and runs the 2s pulse.
 */
export function PulsingDot({
  color = "green",
  pulse = false,
  size = 6,
}: {
  color?: DotColor;
  pulse?: boolean;
  size?: number;
}) {
  return (
    <span
      className={`inline-block shrink-0 rounded-full ${pulse ? "outbreak-pulse" : ""}`}
      style={{ width: size, height: size, backgroundColor: COLORS[color] }}
    />
  );
}
