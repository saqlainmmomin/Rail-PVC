"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { ContractForm } from "@/components/contracts/ContractForm";
import type { ContractFormValues } from "@/lib/contracts-schema";

type CreatedContract = { id: string };

export default function NewContractPage() {
  const router = useRouter();
  const [serverFieldError, setServerFieldError] = useState<
    { field: keyof ContractFormValues; message: string } | null
  >(null);

  async function onSubmit(values: ContractFormValues) {
    setServerFieldError(null);
    try {
      const created = await apiFetch<CreatedContract>("/api/contracts", {
        method: "POST",
        body: values,
      });
      router.push(`/contracts/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        // 409 conflict on agreement_number uniqueness → inline error
        // (apiFetch already toasted, but inline placement is more useful).
        const isAgreementConflict =
          err.status === 409 ||
          (err.detail?.code === "conflict" &&
            err.message.toLowerCase().includes("agreement"));
        if (isAgreementConflict) {
          setServerFieldError({
            field: "agreement_number",
            message: err.message || "Agreement number already in use",
          });
        }
      }
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <Link
          href="/contracts"
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Contracts
        </Link>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          New contract
        </h1>
        <p className="text-[13px] text-slate-500">
          Creates a Draft contract. You can keep configuring schedules and items
          on the detail page after this step.
        </p>
      </header>

      <ContractForm
        onSubmit={onSubmit}
        serverFieldError={serverFieldError}
        submitLabel="Create contract"
      />
    </div>
  );
}
