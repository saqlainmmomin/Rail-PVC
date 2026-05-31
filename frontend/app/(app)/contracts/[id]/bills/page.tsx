"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Receipt } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { BillForm } from "@/components/contracts/BillForm";
import { formatINRWithSymbol } from "@/lib/format";

interface Bill {
  id: string;
  contract_id: string;
  bill_number: number;
  bill_date: string | null;
  measurement_date: string;
  gross_amount: string | number | null;
  net_amount: string | number | null;
  status: string;
}

function statusVariant(
  s: string,
): "draft" | "approved" | "superseded" | "blocked" | "neutral" {
  if (s === "Approved") return "approved";
  if (s === "Superseded") return "superseded";
  if (s === "ExceptionFlagged") return "blocked";
  if (s === "Draft") return "draft";
  return "neutral";
}

export default function BillsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<Bill[]>({
    queryKey: ["contract-bills", id],
    queryFn: () => apiFetch<Bill[]>(`/api/contracts/${id}/bills`),
  });

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link
          href={`/contracts/${id}`}
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Contract
        </Link>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Bills
        </h1>
        <p className="text-[13px] text-slate-500">
          Create a running bill, then enter its lines and recoveries.
        </p>
      </header>

      <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div
          className="px-5 py-3 grid grid-cols-[80px_140px_140px_1fr_100px_80px] gap-4
                     text-[11px] uppercase tracking-wider text-slate-500 font-medium
                     border-b border-slate-200 bg-slate-50"
        >
          <div>Bill no.</div>
          <div>Bill date</div>
          <div>Measurement</div>
          <div className="text-right">Gross</div>
          <div>Status</div>
          <div />
        </div>

        {isLoading && (
          <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
        )}

        {isError && (
          <div className="px-5 py-6 text-[13px] text-red-600">
            {error instanceof ApiError && error.status === 404
              ? "Contract not found"
              : error instanceof Error
                ? error.message
                : "Failed to load bills"}
          </div>
        )}

        {!isLoading && !isError && data?.length === 0 && (
          <div className="px-5 py-8 text-center text-[13px] text-slate-400">
            <Receipt
              className="h-4 w-4 mx-auto mb-2 text-slate-300"
              strokeWidth={1.75}
            />
            No bills yet. Add the first one below.
          </div>
        )}

        {data?.map((b, i) => (
          <div
            key={b.id}
            className={
              "px-5 h-12 grid grid-cols-[80px_140px_140px_1fr_100px_80px] gap-4 items-center text-[13px] " +
              (i < data.length - 1 ? "border-b border-slate-100" : "")
            }
          >
            <div className="font-medium text-slate-900">{b.bill_number}</div>
            <div className="text-slate-600 font-mono text-[12px]">
              {b.bill_date ?? "—"}
            </div>
            <div className="text-slate-600 font-mono text-[12px]">
              {b.measurement_date}
            </div>
            <div className="text-right font-mono text-[12px] text-slate-700">
              {formatINRWithSymbol(b.gross_amount)}
            </div>
            <div>
              <Badge variant={statusVariant(b.status)}>{b.status}</Badge>
            </div>
            <div className="flex justify-end">
              <Link href={`/contracts/${id}/bills/${b.id}`}>
                <Button variant="ghost" size="sm">
                  View
                </Button>
              </Link>
            </div>
          </div>
        ))}
      </div>

      <div className="border border-slate-200 rounded-xl p-5 bg-white">
        <h3 className="text-[14px] font-medium text-slate-900 mb-3">New bill</h3>
        <BillForm
          contractId={id}
          onCreated={() =>
            queryClient.invalidateQueries({ queryKey: ["contract-bills", id] })
          }
        />
      </div>
    </div>
  );
}
