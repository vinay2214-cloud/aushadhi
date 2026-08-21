import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  title = "Nothing here yet",
  message,
  action,
  icon: Icon = Inbox,
}: {
  title?: string;
  message?: string;
  action?: ReactNode;
  icon?: typeof Inbox;
}) {
  return (
    <div className="au-fade flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <Icon size={48} strokeWidth={1.25} color="#52525B" />
      <p className="text-[16px] text-[#A1A1AA]">{title}</p>
      {message ? <p className="text-[14px] text-[#52525B]">{message}</p> : null}
      {action}
    </div>
  );
}
