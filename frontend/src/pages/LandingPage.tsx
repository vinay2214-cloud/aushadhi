import { useEffect, useRef } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { AushdhiLogo } from "../components/shared/AushdhiLogo";

const AGENTS = [
  {
    number: "01",
    name: "SENTINEL",
    color: "#71717A",
    tag: "Firestore",
    description:
      "Polls every health center every 30 minutes. Detects threshold breaches. Fires the pipeline automatically.",
  },
  {
    number: "02",
    name: "DQMS",
    color: "#3B82F6",
    tag: "DQMS Rules",
    description:
      "Validates and cleans consumption data. Rejects impossible values. Scores data quality per center.",
  },
  {
    number: "03",
    name: "FORECAST",
    color: "#A855F7",
    tag: "Gemini 3.5 Flash",
    description:
      "Calls Gemini 3.5 Flash to predict demand and detect disease clusters from consumption signatures.",
  },
  {
    number: "04",
    name: "PROCUREMENT",
    color: "#22C55E",
    tag: "Haversine Routing",
    description:
      "Finds the nearest warehouse. Calculates distance. Auto-generates a purchase order. No approval needed.",
  },
  {
    number: "05",
    name: "ALERT",
    color: "#F97316",
    tag: "Cloud Logging",
    description:
      "Notifies the District Health Officer. Generates compliance reports. Logs everything to Cloud Logging.",
  },
] as const;

const STATS = [
  { value: "6", label: "Critical Stockouts Detected", live: true },
  { value: "8", label: "Health Centers Monitored", live: false },
  { value: "88%", label: "Outbreak Detection Confidence", live: false },
] as const;

const IMPACT = [
  { value: "40%", text: "of Indian rural health centers run out of essential medicines monthly" },
  { value: "3–5 days", text: "earlier than manual surveillance — our outbreak detection lead time" },
  { value: "₹0", text: "human intervention required in the full agent pipeline" },
] as const;

const STACK = [
  "Gemini 3.5 Flash",
  "Vertex AI",
  "Cloud Run",
  "Firestore",
  "Pub/Sub",
  "Cloud Scheduler",
  "Google ADK",
] as const;

const EVIDENCE = ["ORS 3.8×", "Zinc 3.6×", "IV Saline 3.7×"] as const;

function PrimaryButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-md px-7 py-3 text-[14px] font-semibold transition-colors duration-150"
      style={{ backgroundColor: "#FAFAFA", color: "#09090B" }}
      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#E4E4E7")}
      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#FAFAFA")}
    >
      {children}
    </button>
  );
}

/** Staggered slide-in for the pipeline steps as they scroll into view. */
function usePipelineReveal() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const steps = Array.from(root.querySelectorAll<HTMLElement>("[data-step]"));
    if (typeof IntersectionObserver === "undefined") {
      steps.forEach((el) => el.classList.add("step-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target as HTMLElement;
          const index = Number(el.dataset["step"] ?? 0);
          window.setTimeout(() => el.classList.add("step-visible"), index * 150);
          observer.unobserve(el);
        });
      },
      { threshold: 0.2 },
    );

    steps.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return containerRef;
}

export function LandingPage() {
  const navigate = useNavigate();
  const pipelineRef = usePipelineReveal();

  const goToDashboard = () => navigate({ to: "/dashboard" });

  const scrollToHowItWorks = () => {
    document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div style={{ backgroundColor: "#09090B", color: "#FAFAFA" }}>
      {/* ── SECTION 1: NAVIGATION ─────────────────────────────── */}
      <nav
        className="fixed inset-x-0 top-0 z-50 flex h-14 items-center justify-between"
        style={{
          padding: "0 40px",
          backgroundColor: "rgba(9,9,11,0.85)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Link to="/" aria-label="AUSHADHI home">
          <AushdhiLogo size="sm" showTagline={false} />
        </Link>
        <button
          onClick={goToDashboard}
          className="rounded-md px-4 py-1.5 text-[13px] font-medium transition-colors duration-150"
          style={{ color: "#FAFAFA", border: "1px solid rgba(255,255,255,0.15)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#FAFAFA";
            e.currentTarget.style.color = "#09090B";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "#FAFAFA";
          }}
        >
          Enter Dashboard →
        </button>
      </nav>

      {/* ── SECTION 2: HERO ───────────────────────────────────── */}
      <header className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">
        {/* Static radial wash behind the copy */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{
            zIndex: 0,
            width: 800,
            height: 800,
            background:
              "radial-gradient(circle, rgba(34,197,94,0.04) 0%, rgba(59,130,246,0.03) 40%, transparent 70%)",
          }}
        />

        <div className="relative mx-auto max-w-[860px]" style={{ zIndex: 1 }}>
          <span
            className="animate-fade-in inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[12px]"
            style={{
              animationDelay: "0.3s",
              backgroundColor: "rgba(34,197,94,0.08)",
              border: "1px solid rgba(34,197,94,0.2)",
              color: "#22C55E",
            }}
          >
            <span className="animate-pulse-dot">●</span>
            LIVE — Monitoring East Godavari &amp; Krishna Districts
          </span>

          <h1
            className="animate-fade-in mt-8 font-bold"
            style={{
              animationDelay: "0.1s",
              fontSize: "clamp(40px, 6vw, 72px)",
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
            }}
          >
            <span style={{ color: "#FAFAFA" }}>Medicine Stockouts Kill.</span>
            <br />
            <span style={{ color: "#22C55E" }}>AUSHADHI Stops Them.</span>
          </h1>

          <p
            className="animate-fade-in mx-auto mt-6 max-w-[560px]"
            style={{ animationDelay: "0.2s", fontSize: 18, color: "#A1A1AA", lineHeight: 1.7 }}
          >
            Five autonomous AI agents monitor every health center in rural Andhra Pradesh —
            detecting stockouts before they happen and disease outbreaks before any doctor
            reports them.
          </p>

          <div
            className="animate-fade-in mt-10 flex flex-wrap items-center justify-center gap-3"
            style={{ animationDelay: "0.3s" }}
          >
            <PrimaryButton onClick={goToDashboard}>Enter Dashboard →</PrimaryButton>
            <button
              onClick={scrollToHowItWorks}
              className="rounded-md px-7 py-3 text-[14px] transition-colors duration-150"
              style={{
                backgroundColor: "transparent",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "#A1A1AA",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
                e.currentTarget.style.color = "#FAFAFA";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                e.currentTarget.style.color = "#A1A1AA";
              }}
            >
              Watch How It Works ↓
            </button>
          </div>

          <div
            className="animate-fade-in mt-16 flex flex-wrap items-center justify-center gap-8"
            style={{ animationDelay: "0.5s" }}
          >
            {STATS.map((stat, i) => (
              <div key={stat.label} className="flex items-center gap-8">
                {i > 0 ? (
                  <span
                    aria-hidden="true"
                    style={{ width: 1, height: 40, backgroundColor: "rgba(255,255,255,0.06)" }}
                  />
                ) : null}
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <span
                      className="font-bold tabular-nums"
                      style={{ fontSize: 36, color: "#FAFAFA" }}
                    >
                      {stat.value}
                    </span>
                    {stat.live ? (
                      <span
                        className="inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.08em]"
                        style={{ color: "#22C55E" }}
                      >
                        <span
                          className="animate-pulse-dot inline-block size-1.5 rounded-full"
                          style={{ backgroundColor: "#22C55E" }}
                        />
                        Live
                      </span>
                    ) : null}
                  </div>
                  <p style={{ fontSize: 12, color: "#52525B", marginTop: 4 }}>{stat.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── SECTION 3: ALERT SHOWCASE ─────────────────────────── */}
      <section style={{ backgroundColor: "#0D0D0F", padding: "80px 40px" }}>
        <div className="mx-auto max-w-[1000px]">
          <p
            className="text-center uppercase"
            style={{
              fontSize: 11,
              color: "#52525B",
              letterSpacing: "0.08em",
              marginBottom: 24,
            }}
          >
            Real Outbreak Detection
          </p>

          <article
            className="animate-card-rise"
            style={{
              backgroundColor: "#111113",
              border: "1px solid rgba(255,255,255,0.07)",
              borderLeft: "3px solid #F97316",
              borderRadius: 8,
              padding: "24px 28px",
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span
                className="uppercase tracking-[0.06em]"
                style={{ fontSize: 11, color: "#F97316" }}
              >
                ⬡ Outbreak Alert
              </span>
              <span className="flex items-center gap-3">
                <span style={{ fontSize: 12, color: "#A1A1AA" }}>88% confidence</span>
                <span
                  className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase"
                  style={{ backgroundColor: "#F97316", color: "#09090B" }}
                >
                  High Risk
                </span>
              </span>
            </div>

            <p style={{ fontSize: 16, color: "#FAFAFA", lineHeight: 1.6, marginTop: 16 }}>
              A synchronized 3.8× surge in ORS, Zinc, and IV fluid consumption across Amalapuram
              and Razole PHCs strongly signals an emerging Cholera or severe Diarrheal outbreak
              following recent delta flooding.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              {EVIDENCE.map((item) => (
                <span
                  key={item}
                  className="font-mono"
                  style={{
                    backgroundColor: "rgba(239,68,68,0.08)",
                    border: "1px solid rgba(239,68,68,0.2)",
                    color: "#EF4444",
                    fontSize: 13,
                    padding: "4px 12px",
                    borderRadius: 4,
                  }}
                >
                  {item}
                </span>
              ))}
            </div>

            <p style={{ fontSize: 12, color: "#52525B", fontStyle: "italic", marginTop: 20 }}>
              Detected 3–5 days before manual surveillance
            </p>
          </article>
        </div>
      </section>

      {/* ── SECTION 4: HOW IT WORKS ───────────────────────────── */}
      <section id="how-it-works" style={{ backgroundColor: "#09090B", padding: "100px 40px" }}>
        <div className="mx-auto max-w-[1000px]">
          <p
            className="uppercase"
            style={{ fontSize: 11, color: "#52525B", letterSpacing: "0.08em" }}
          >
            The Five-Agent Pipeline
          </p>
          <h2
            className="font-semibold"
            style={{ fontSize: 36, color: "#FAFAFA", marginTop: 12, marginBottom: 16 }}
          >
            Autonomous from alert to action.
          </h2>
          <p style={{ fontSize: 16, color: "#A1A1AA" }}>
            Zero humans in the loop. Every step agent-driven.
          </p>

          <div ref={pipelineRef} className="relative mt-14 pl-8">
            <span
              aria-hidden="true"
              className="absolute bottom-2 left-[5px] top-2"
              style={{ width: 2, backgroundColor: "#1A1A1E" }}
            />
            {AGENTS.map((agent, index) => (
              <div
                key={agent.name}
                data-step={index}
                className="pipeline-step relative pb-10 last:pb-0"
              >
                <span
                  className="absolute -left-8 top-1 block rounded-full"
                  style={{ width: 12, height: 12, backgroundColor: agent.color }}
                />
                <div className="flex flex-wrap items-center gap-3">
                  <span style={{ fontSize: 11, color: "#52525B" }}>{agent.number}</span>
                  <span className="font-semibold" style={{ fontSize: 16, color: agent.color }}>
                    {agent.name}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      border: "1px solid rgba(255,255,255,0.08)",
                      backgroundColor: "rgba(255,255,255,0.03)",
                      padding: "2px 8px",
                      borderRadius: 4,
                      color: "#52525B",
                    }}
                  >
                    {agent.tag}
                  </span>
                </div>
                <p style={{ fontSize: 14, color: "#A1A1AA", marginTop: 8, maxWidth: 620 }}>
                  {agent.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECTION 5: IMPACT ─────────────────────────────────── */}
      <section style={{ backgroundColor: "#0D0D0F", padding: "80px 40px" }}>
        <div className="mx-auto flex max-w-[1000px] flex-wrap items-start justify-center gap-16">
          {IMPACT.map((item) => (
            <div key={item.value} className="text-center">
              <p className="font-bold" style={{ fontSize: 48, color: "#FAFAFA" }}>
                {item.value}
              </p>
              <p
                className="mx-auto"
                style={{ fontSize: 14, color: "#A1A1AA", maxWidth: 240, marginTop: 8 }}
              >
                {item.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 6: TECH STACK ─────────────────────────────── */}
      <section style={{ backgroundColor: "#09090B", padding: "60px 40px" }} className="text-center">
        <p
          className="uppercase"
          style={{ fontSize: 11, color: "#52525B", letterSpacing: "0.08em", marginBottom: 28 }}
        >
          Built on Google Cloud
        </p>
        <div className="mx-auto flex max-w-[900px] flex-wrap items-center justify-center gap-3">
          {STACK.map((tech) => (
            <span
              key={tech}
              className="transition-colors duration-150"
              style={{
                border: "1px solid rgba(255,255,255,0.08)",
                backgroundColor: "rgba(255,255,255,0.02)",
                padding: "8px 16px",
                borderRadius: 6,
                fontSize: 13,
                color: "#71717A",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                e.currentTarget.style.color = "#A1A1AA";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.color = "#71717A";
              }}
            >
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* ── SECTION 7: CTA FOOTER ─────────────────────────────── */}
      <footer
        className="text-center"
        style={{
          backgroundColor: "#09090B",
          padding: "100px 40px",
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <AushdhiLogo size="lg" showTagline className="mx-auto mb-8" />
        <h2 className="font-semibold" style={{ fontSize: 32, color: "#FAFAFA", marginBottom: 8 }}>
          Watch Five Agents Work.
        </h2>
        <p style={{ fontSize: 16, color: "#A1A1AA", marginBottom: 32 }}>
          Real data. Real Gemini calls. Real East Godavari health centers.
        </p>
        <PrimaryButton onClick={goToDashboard}>Open Dashboard →</PrimaryButton>
        <p style={{ fontSize: 12, color: "#3F3F46", marginTop: 48 }}>
          Built for the All Things Agentic Hackathon by Google
        </p>
      </footer>
    </div>
  );
}

export default LandingPage;
