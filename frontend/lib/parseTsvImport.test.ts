import { describe, it, expect } from "vitest";
import { parseTsvImport } from "./parseTsvImport";

// Pin REVIEW.md H-1: unknown classification values must be rejected to
// errors[], not silently coerced.

const HEADER_OK =
  "IC-1\tCement bag\tbag\t100\t100\t450\t440\tTRUE\t";

describe("parseTsvImport", () => {
  it("accepts a well-formed row with TRUE cement + blank steel", () => {
    const result = parseTsvImport(HEADER_OK);
    expect(result.errors).toEqual([]);
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].is_cement_item).toBe(true);
    expect(result.rows[0].steel_subtype).toBe(null);
  });

  it("accepts case-insensitive cement accept-list (true/false/yes/no/1/0)", () => {
    const inputs = ["TRUE", "true", "yes", "YES", "1", "false", "FALSE", "no", "0", ""];
    for (const v of inputs) {
      const line = `IC\td\tu\t1\t1\t1\t1\t${v}\t`;
      const result = parseTsvImport(line);
      expect(result.errors).toEqual([]);
      expect(result.rows).toHaveLength(1);
    }
  });

  it("rejects garbage in is_cement_item (the H-1 case)", () => {
    const line = "IC-1\tCement bag\tbag\t100\t100\t450\t440\tTru\t";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toMatch(/is_cement_item.*Tru/);
  });

  it("rejects unknown is_cement_item tokens like 'checkmark'", () => {
    const line = "IC-1\td\tu\t1\t1\t1\t1\tcheckmark\t";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors[0]).toMatch(/is_cement_item/);
  });

  it("accepts valid steel subtypes", () => {
    for (const s of ["angles", "plates", "other_sections", "tmt"]) {
      const line = `IS\td\tu\t1\t1\t1\t1\tFALSE\t${s}`;
      const result = parseTsvImport(line);
      expect(result.errors).toEqual([]);
      expect(result.rows[0].steel_subtype).toBe(s);
    }
  });

  it("rejects unknown steel subtypes — uppercase TMT (the H-1 case)", () => {
    const line = "IS-1\tBar\tkg\t100\t100\t60\t58\tFALSE\tTMT";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors[0]).toMatch(/steel_subtype.*TMT/);
  });

  it("rejects unknown steel subtypes — 'rebar' is not in VALID_STEEL_SUBTYPES", () => {
    const line = "IS-1\tBar\tkg\t100\t100\t60\t58\tFALSE\trebar";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors[0]).toMatch(/steel_subtype.*rebar/);
  });

  it("treats blank steel_subtype as null (non-steel item)", () => {
    const line = "IC\td\tu\t1\t1\t1\t1\tTRUE\t";
    const result = parseTsvImport(line);
    expect(result.errors).toEqual([]);
    expect(result.rows[0].steel_subtype).toBe(null);
  });

  it("treats blank is_cement_item as false (the common BoQ convention)", () => {
    const line = "I\td\tu\t1\t1\t1\t1\t\tangles";
    const result = parseTsvImport(line);
    expect(result.errors).toEqual([]);
    expect(result.rows[0].is_cement_item).toBe(false);
  });

  it("reports both row-level errors and skips that row from rows[]", () => {
    const raw = [
      "IC-1\tCement\tbag\t100\t100\t450\t440\tTRUE\t",
      "IS-1\tBar\tkg\t100\t100\t60\t58\tFALSE\tTMT",
      "IO-1\tOther\tnos\t10\t10\t1\t1\tFALSE\t",
    ].join("\n");
    const result = parseTsvImport(raw);
    expect(result.rows).toHaveLength(2);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toMatch(/Row 2/);
  });

  it("rejects rows with too few columns", () => {
    const line = "only\tthree\tcolumns";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors[0]).toMatch(/expected 8–9 columns/);
  });

  it("rejects non-numeric quantity strings", () => {
    const line = "IC\td\tu\tabc\t1\t1\t1\tFALSE\t";
    const result = parseTsvImport(line);
    expect(result.rows).toHaveLength(0);
    expect(result.errors[0]).toMatch(/original_qty.*abc/);
  });
});
