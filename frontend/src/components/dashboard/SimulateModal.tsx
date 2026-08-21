import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Beaker, Loader2, X } from "lucide-react";
import { simulateOutbreak } from "../../api/outbreaks";

const DEFAULTS = {
  district: "East Godavari",
  subdistrict: "Razole",
  disease: "Cholera",
  medicine: "ORS",
  consumption_multiplier: 4,
  affected_centers: 3,
};

export function SimulateModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState(DEFAULTS);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => simulateOutbreak(form),
    onSuccess: () => {
      toast.success("Simulation dispatched — watch the agent feed");
      queryClient.invalidateQueries({ queryKey: ["outbreaks"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      onClose();
    },
    onError: () => toast.error("Simulation failed"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#09090B]/80 p-4">
      <div className="panel-card w-full max-w-md">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Beaker className="size-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-slate-100">Simulate Stockout / Outbreak</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-slate-500 hover:bg-white/[0.06] hover:text-slate-200"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {(
            [
              ["district", "District"],
              ["subdistrict", "Subdistrict"],
              ["disease", "Disease"],
              ["medicine", "Medicine"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="block">
              <span className="text-[11px] uppercase tracking-wide text-slate-500">{label}</span>
              <input
                value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                className="mt-1 w-full rounded-md border border-white/[0.10] bg-[#09090B] px-3 py-2 text-sm text-slate-200 outline-none focus:border-[#22C55E]"
              />
            </label>
          ))}
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[11px] uppercase tracking-wide text-slate-500">
                Consumption ×
              </span>
              <input
                type="number"
                value={form.consumption_multiplier}
                onChange={(e) =>
                  setForm((f) => ({ ...f, consumption_multiplier: Number(e.target.value) }))
                }
                className="mt-1 w-full rounded-md border border-white/[0.10] bg-[#09090B] px-3 py-2 text-sm text-slate-200 outline-none focus:border-[#22C55E]"
              />
            </label>
            <label className="block">
              <span className="text-[11px] uppercase tracking-wide text-slate-500">Centers</span>
              <input
                type="number"
                value={form.affected_centers}
                onChange={(e) =>
                  setForm((f) => ({ ...f, affected_centers: Number(e.target.value) }))
                }
                className="mt-1 w-full rounded-md border border-white/[0.10] bg-[#09090B] px-3 py-2 text-sm text-slate-200 outline-none focus:border-[#22C55E]"
              />
            </label>
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-white/[0.10] px-3 py-1.5 text-[12px] text-slate-400 hover:bg-white/[0.06]"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 className="size-3.5 animate-spin" /> : null}
            Run Simulation
          </button>
        </div>
      </div>
    </div>
  );
}
