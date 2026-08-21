export type LogoSize = "sm" | "md" | "lg" | "icon-only";

const SIZES: Record<Exclude<LogoSize, "icon-only">, { icon: number; name: number; tagline: number }> =
  {
    sm: { icon: 20, name: 14, tagline: 10 },
    md: { icon: 28, name: 16, tagline: 11 },
    lg: { icon: 36, name: 20, tagline: 12 },
  };

/**
 * The mark: a tulsi/neem leaf (aushadhi = medicine/herb) whose three veins
 * terminate in data nodes — the three primary outbreak indicators the system
 * watches (ORS, Zinc, IV Saline).
 *
 * Single colour via currentColor, so it inherits from whatever it sits in.
 */
export function AushdhiMark({
  size = 28,
  className,
}: {
  size?: number;
  className?: string | undefined;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="AUSHADHI"
    >
      {/* Leaf body — pointed oval, tip upward */}
      <path
        d="M16 2.5C22.2 7.4 24.6 15.2 16 29.5C7.4 15.2 9.8 7.4 16 2.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      {/* Central stem */}
      <path
        d="M16 28.5V9.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
      {/* Three veins, each ending in a node */}
      <path d="M16 21.4L11.3 17.6" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M16 16.6L20.7 12.8" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M16 12.2L12.6 9.1" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
      <circle cx="10.6" cy="17.1" r="2" fill="currentColor" />
      <circle cx="21.4" cy="12.3" r="2" fill="currentColor" />
      <circle cx="11.9" cy="8.6" r="2" fill="currentColor" />
    </svg>
  );
}

export function AushdhiLogo({
  size = "md",
  className,
  showTagline,
}: {
  size?: LogoSize;
  className?: string | undefined;
  showTagline?: boolean | undefined;
}) {
  if (size === "icon-only") {
    return <AushdhiMark size={SIZES.md.icon} className={className} />;
  }

  const scale = SIZES[size];
  // Tagline defaults on for md/lg, off for the compact sm mark.
  const withTagline = showTagline ?? size !== "sm";

  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <AushdhiMark size={scale.icon} className="shrink-0 text-[#22C55E]" />
      <span className="flex min-w-0 flex-col leading-none">
        <span
          className="font-bold tracking-[0.02em] text-[#FAFAFA]"
          style={{ fontSize: scale.name }}
        >
          AUSHADHI
        </span>
        {withTagline ? (
          <span className="mt-1 text-[#52525B]" style={{ fontSize: scale.tagline }}>
            Medicine Supply Intelligence
          </span>
        ) : null}
      </span>
    </span>
  );
}

export default AushdhiLogo;
