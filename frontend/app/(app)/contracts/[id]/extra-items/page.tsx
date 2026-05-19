"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { ExtraItemDecisionList } from "@/components/contracts/ExtraItemDecisionList";

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
}

interface Decision {
  id: string;
  item_id: string;
  eligible: boolean | null;
  notes: string | null;
}

export default function ExtraItemsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const schedules = useQuery<Schedule[]>({
    queryKey: ["contract-schedules", id],
    queryFn: () => apiFetch<Schedule[]>(`/api/contracts/${id}/schedules`),
  });

  const decisions = useQuery<Decision[]>({
    queryKey: ["extra-item-decisions", id],
    queryFn: () =>
      apiFetch<Decision[]>(`/api/contracts/${id}/extra-item-decisions`),
  });

  const isLoading = schedules.isLoading || decisions.isLoading;

  if (schedules.isError || decisions.isError) {
    const err = schedules.error ?? decisions.error;
    const msg =
      err instanceof ApiError && err.status === 404
        ? "Contract not found"
        : err instanceof Error
          ? err.message
          : "Failed to load";
    return (
      <div className="space-y-4">
        <Link
          href={`/contracts/${id}`}
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Back to contract
        </Link>
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {msg}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link
          href={`/contracts/${id}`}
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Back to contract
        </Link>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Extra-item decisions
        </h1>
        <p className="text-[13px] text-slate-500">
          Each ExtraNS item needs an explicit eligibility verdict before a PVC
          run can proceed. Undecided rows block the engine at run time.
        </p>
      </header>

      {isLoading ? (
        <div className="text-[13px] text-slate-400 py-12 text-center">
          Loading…
        </div>
      ) : (
        <ExtraItemDecisionList
          contractId={id}
          schedules={schedules.data ?? []}
          decisions={decisions.data ?? []}
        />
      )}
    </div>
  );
}
