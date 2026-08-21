import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "../pages/LandingPage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AUSHADHI — Autonomous Medicine Supply Intelligence" },
      {
        name: "description",
        content:
          "Five autonomous AI agents monitor every health center in rural Andhra Pradesh — detecting stockouts before they happen and disease outbreaks before any doctor reports them.",
      },
      { property: "og:title", content: "AUSHADHI — Autonomous Medicine Supply Intelligence" },
      {
        property: "og:description",
        content:
          "Stockout prediction and outbreak detection for rural health centers, powered by Gemini 3.5 Flash on Google Cloud.",
      },
    ],
  }),
  component: LandingPage,
});
