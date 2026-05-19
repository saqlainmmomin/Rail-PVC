"use client";

import { useMemo } from "react";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
}

interface ContractItem {
  id: string;
  item_code: string;
  description: string;
}

interface Decision {
  id: string;
  item_id: string;
  eligible: boolean | null;
  notes: string | null;
}

type Row = {
  item_id: string;
  item_code: string;
  description: string;
  schedule_name: string;
  eligible: boolean | null;
};

type Verdict = "yes" | "no" | "undecided";

function verdictOf(eligible: boolean | null): Verdict {
  if (eligible === true) return "yes";
  if (eligible === false) return "no";
  return "undecided";
}

function eligibleFor(v: Verdict): boolean | null {
  if (v === "yes") return true;
  if (v === "no") return false;
  return null;
}

export function ExtraItemDecisionList({
  contractId,
  schedules,
  decisions,
}: {
  contractId: string;
  schedules: Schedule[];
  decisions: Decision[];
}) {
  const queryClient = useQueryClient();

  const extraNsSchedules = useMemo(
    () => schedules.filter((s) => s.schedule_type === "ExtraNS"),
    [schedules],
  );

  const itemQueries = useQueries({
    queries: extraNsSchedules.map((s) => ({
      queryKey: ["schedule-items", s.id],
      queryFn: () => apiFetch<ContractItem[]>(`/api/schedules/${s.id}/items`),
    })),
  });

  const decisionsByItem = useMemo(() => {
    const m = new Map<string, Decision>();
    for (const d of decisions) m.set(d.item_id, d);
    return m;
  }, [decisions]);

  const rows: Row[] = useMemo(() => {
    const out: Row[] = [];
    extraNsSchedules.forEach((s, i) => {
      const items = itemQueries[i]?.data ?? [];
      for (const item of items) {
        const d = decisionsByItem.get(item.id);
        out.push({
          item_id: item.id,
          item_code: item.item_code,
          description: item.description,
          schedule_name: s.name,
          eligible: d ? d.eligible : null,
        });
      }
    });
    return out;
  }, [extraNsSchedules, itemQueries, decisionsByItem]);

  const undecidedCount = rows.filter((r) => r.eligible === null).length;
  const isLoading = itemQueries.some((q) => q.isLoading);

  const setVerdict = useMutation({
    mutationFn: async (args: { item_id: string; eligible: boolean | null }) => {
      await apiFetch(`/api/contracts/${contractId}/extra-item-decisions`, {
        method: "POST",
        body: args,
      });
    },
    onMutate: async (args) => {
      await queryClient.cancelQueries({
        queryKey: ["extra-item-decisions", contractId],
      });
      const previous = queryClient.getQueryData<Decision[]>([
        "extra-item-decisions",
        contractId,
      ]);
      queryClient.setQueryData<Decision[]>(
        ["extra-item-decisions", contractId],
        (old) => {
          const list = old ? [...old] : [];
          const idx = list.findIndex((d) => d.item_id === args.item_id);
          const stub: Decision = {
            id: idx >= 0 ? list[idx].id : `optimistic-${args.item_id}`,
            item_id: args.item_id,
            eligible: args.eligible,
            notes: null,
          };
          if (idx >= 0) list[idx] = stub;
          else list.push(stub);
          return list;
        },
      );
      return { previous };
    },
    onError: (_err, _args, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(
          ["extra-item-decisions", contractId],
          ctx.previous,
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["extra-item-decisions", contractId],
      });
    },
  });

  return (
    <div className="space-y-4">
      {rows.length > 0 &&
        (undecidedCount === 0 ? (
          <div className="text-[13px] text-green-800 bg-green-50 border border-green-200 rounded-lg px-4 py-2.5">
            All extra items decided — PVC run can proceed.
          </div>
        ) : (
          <div className="text-[13px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5">
            {undecidedCount} item(s) undecided — PVC run will be blocked until
            all are decided.
          </div>
        ))}

      <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div
          className="px-5 py-3 grid grid-cols-[120px_1fr_160px_220px] gap-4 text-[11px]
                     uppercase tracking-wider text-slate-500 font-medium
                     border-b border-slate-200 bg-slate-50"
        >
          <div>Code</div>
          <div>Description</div>
          <div>Schedule</div>
          <div>Eligibility</div>
        </div>
        {isLoading && (
          <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
        )}
        {!isLoading && rows.length === 0 && (
          <div className="px-5 py-6 text-[13px] text-slate-400">
            No extra-item rows yet. Add an ExtraNS schedule and items first.
          </div>
        )}
        {rows.map((r, i) => {
          const v = verdictOf(r.eligible);
          return (
            <div
              key={r.item_id}
              className={
                "px-5 h-12 grid grid-cols-[120px_1fr_160px_220px] gap-4 items-center text-[13px] " +
                (i < rows.length - 1 ? "border-b border-slate-100" : "")
              }
            >
              <div className="font-mono text-[12px] text-slate-700">
                {r.item_code}
              </div>
              <div className="text-slate-900 truncate">{r.description}</div>
              <div className="text-slate-600">{r.schedule_name}</div>
              <div className="flex gap-1">
                {(["yes", "no", "undecided"] as Verdict[]).map((opt) => (
                  <Button
                    key={opt}
                    type="button"
                    size="sm"
                    variant={v === opt ? "primary" : "secondary"}
                    onClick={() =>
                      setVerdict.mutate({
                        item_id: r.item_id,
                        eligible: eligibleFor(opt),
                      })
                    }
                  >
                    {opt === "yes" ? "Yes" : opt === "no" ? "No" : "Undecided ⚠"}
                  </Button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
