import { AlertTriangle } from "lucide-react";

export function ErrorState({
  title = "Could not load data",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg px-6 py-12 text-center"
      style={{ border: "1px solid #EF44443A", backgroundColor: "#EF44440D" }}
    >
      <AlertTriangle size={32} strokeWidth={1.5} color="#EF4444" />
      <div>
        <p className="text-[15px] text-[#FAFAFA]">{title}</p>
        {message ? <p className="mt-1 text-[13px] text-[#A1A1AA]">{message}</p> : null}
      </div>
      {onRetry ? (
        <button
          onClick={onRetry}
          className="rounded-md px-3 py-1.5 text-[12px] font-medium text-[#A1A1AA] transition-colors hover:bg-white/[0.06]"
          style={{ border: "1px solid var(--border-default)" }}
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
