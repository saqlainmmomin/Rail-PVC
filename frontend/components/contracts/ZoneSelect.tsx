import { forwardRef, type SelectHTMLAttributes } from "react";
import { VALID_ZONES } from "@/lib/zones";

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> & {
  error?: string;
};

export const ZoneSelect = forwardRef<HTMLSelectElement, Props>(function ZoneSelect(
  { error, className, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      {...rest}
      className={
        "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
        "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500 " +
        (error ? "border-red-300 " : "") +
        (className ?? "")
      }
    >
      <option value="">— Select zone —</option>
      {VALID_ZONES.map((z) => (
        <option key={z.code} value={z.code}>
          {z.label}
        </option>
      ))}
    </select>
  );
});
