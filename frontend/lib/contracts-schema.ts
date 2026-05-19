import { z } from "zod";
import { ZONE_CODES } from "./zones";

// Mirror of backend `ContractCreate` (backend/api/contracts.py). Server-side
// rules that cannot be validated client-side (e.g. agreement_number
// uniqueness) are not duplicated here — see WORKPLAN.md Q6.
//
// overall_rebate is stored as a fraction (0.15 = 15%); DB column is
// NUMERIC(5,4), max 9.9999. UI labels must say so explicitly.

const optionalDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "expected YYYY-MM-DD")
  .optional()
  .or(z.literal("").transform(() => undefined));

const positiveNumber = z
  .number({ message: "expected a number" })
  .positive("must be > 0");

const optionalPositive = positiveNumber.optional();

export const contractCreateSchema = z
  .object({
    tender_number: z.string().min(1, "required"),
    agreement_number: z.string().optional().or(z.literal("").transform(() => undefined)),
    loa_number: z.string().optional().or(z.literal("").transform(() => undefined)),
    loa_date: optionalDate,
    contractor_name: z.string().min(1, "required"),
    work_description: z.string().optional().or(z.literal("").transform(() => undefined)),
    railway_zone: z.enum(ZONE_CODES as unknown as [string, ...string[]]),
    base_month: z
      .string()
      .regex(/^\d{4}-\d{2}-01$/, "must be the first day of the month (YYYY-MM-01)"),
    start_date: optionalDate,
    completion_date: optionalDate,
    contract_value: optionalPositive,
    bid_amount: optionalPositive,
    gst_mode: z.enum(["exclusive", "inclusive"]),
    pvc_applicable: z.boolean(),
    overall_rebate: z
      .number()
      .min(0, "must be ≥ 0")
      .max(9.9999, "must be ≤ 9.9999 (stored as fraction, 0.15 = 15%)")
      .optional(),
  })
  .refine(
    (v) =>
      !v.start_date || !v.completion_date || v.start_date <= v.completion_date,
    { path: ["completion_date"], message: "must be on or after start date" },
  )
  .refine(
    (v) => !v.start_date || v.base_month <= v.start_date,
    { path: ["start_date"], message: "must be on or after base month" },
  )
  .refine(
    (v) =>
      v.bid_amount === undefined ||
      v.contract_value === undefined ||
      v.bid_amount <= v.contract_value,
    { path: ["bid_amount"], message: "must be ≤ contract value" },
  );

export type ContractFormValues = z.infer<typeof contractCreateSchema>;
