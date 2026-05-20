// Pure parser for the items-grid Excel-paste flow. Extracted from ItemsGrid
// so the validation rules can be unit-tested.
//
// Trust rules (REVIEW.md H-1):
// - `is_cement_item` is matched against an explicit accept-list. Unknown
//   strings are rejected to errors[], not silently coerced to false.
// - `steel_subtype` is matched against VALID_STEEL_SUBTYPES (mirroring the
//   backend's frozenset). Unknown subtypes are rejected, not passed through.
// Both flags drive engine W-derivation bucket selection — a silent
// misclassification is a silent PVC error.

export type SteelSubtype = "angles" | "plates" | "other_sections" | "tmt" | null;

export const VALID_STEEL_SUBTYPES = [
  "angles",
  "plates",
  "other_sections",
  "tmt",
] as const;

const CEMENT_TRUE = new Set(["true", "yes", "1"]);
const CEMENT_FALSE = new Set(["false", "no", "0", ""]);

export interface ParsedRow {
  item_code: string;
  description: string;
  unit: string;
  original_qty: number | null;
  revised_qty: number | null;
  base_rate: number | null;
  agreement_rate: number | null;
  is_cement_item: boolean;
  steel_subtype: SteelSubtype;
}

export interface ParseResult {
  rows: ParsedRow[];
  errors: string[];
}

function parseNumeric(raw: string): { value: number | null; ok: boolean } {
  const t = (raw ?? "").trim();
  if (t === "") return { value: null, ok: true };
  const n = Number(t);
  if (Number.isNaN(n)) return { value: null, ok: false };
  return { value: n, ok: true };
}

export function parseTsvImport(raw: string): ParseResult {
  const rows: ParsedRow[] = [];
  const errors: string[] = [];
  const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);

  lines.forEach((line, idx) => {
    const cols = line.split("\t");
    const rowNum = idx + 1;
    if (cols.length < 8) {
      errors.push(
        `Row ${rowNum}: expected 8–9 columns, got ${cols.length}`,
      );
      return;
    }
    const [
      item_code,
      description,
      unit,
      original_qty_raw,
      revised_qty_raw,
      base_rate_raw,
      agreement_rate_raw,
      is_cement_raw,
      steel_subtype_raw,
    ] = cols;

    const rowErrors: string[] = [];

    const oqty = parseNumeric(original_qty_raw);
    if (!oqty.ok) rowErrors.push(`original_qty "${original_qty_raw.trim()}" is not a number`);
    const rqty = parseNumeric(revised_qty_raw);
    if (!rqty.ok) rowErrors.push(`revised_qty "${revised_qty_raw.trim()}" is not a number`);
    const brate = parseNumeric(base_rate_raw);
    if (!brate.ok) rowErrors.push(`base_rate "${base_rate_raw.trim()}" is not a number`);
    const arate = parseNumeric(agreement_rate_raw);
    if (!arate.ok) rowErrors.push(`agreement_rate "${agreement_rate_raw.trim()}" is not a number`);

    const cementToken = (is_cement_raw ?? "").trim().toLowerCase();
    let cement = false;
    if (CEMENT_TRUE.has(cementToken)) {
      cement = true;
    } else if (CEMENT_FALSE.has(cementToken)) {
      cement = false;
    } else {
      rowErrors.push(
        `is_cement_item "${is_cement_raw.trim()}" must be one of TRUE / FALSE / YES / NO / 1 / 0 (case-insensitive, blank = false)`,
      );
    }

    const subtypeToken = (steel_subtype_raw ?? "").trim();
    let subtype: SteelSubtype = null;
    if (subtypeToken === "") {
      subtype = null;
    } else if ((VALID_STEEL_SUBTYPES as readonly string[]).includes(subtypeToken)) {
      subtype = subtypeToken as SteelSubtype;
    } else {
      rowErrors.push(
        `steel_subtype "${subtypeToken}" must be blank or one of ${VALID_STEEL_SUBTYPES.join(", ")}`,
      );
    }

    if (rowErrors.length > 0) {
      errors.push(`Row ${rowNum}: ${rowErrors.join("; ")}`);
      return;
    }

    rows.push({
      item_code: item_code.trim(),
      description: description.trim(),
      unit: unit.trim(),
      original_qty: oqty.value,
      revised_qty: rqty.value,
      base_rate: brate.value,
      agreement_rate: arate.value,
      is_cement_item: cement,
      steel_subtype: subtype,
    });
  });

  return { rows, errors };
}
