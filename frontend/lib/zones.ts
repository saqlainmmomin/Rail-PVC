// Frontend mirror of backend/services/zone_mapping.py:VALID_ZONES.
// 16 Indian Railway zones; codes MUST match the Postgres enum exactly
// (any new zone needs a migration, and this list updated in the same PR).
// Risk-tracked in WORKPLAN.md → Risk Register → "VALID_ZONES drift".
export const VALID_ZONES = [
  { code: "NR",   label: "NR — Northern" },
  { code: "NCR",  label: "NCR — North Central" },
  { code: "NWR",  label: "NWR — North Western" },
  { code: "NER",  label: "NER — North Eastern" },
  { code: "ER",   label: "ER — Eastern" },
  { code: "ECR",  label: "ECR — East Central" },
  { code: "ECOR", label: "ECOR — East Coast" },
  { code: "NFR",  label: "NFR — Northeast Frontier" },
  { code: "SER",  label: "SER — South Eastern" },
  { code: "SECR", label: "SECR — South East Central" },
  { code: "CR",   label: "CR — Central" },
  { code: "WR",   label: "WR — Western" },
  { code: "WCR",  label: "WCR — West Central" },
  { code: "SR",   label: "SR — Southern" },
  { code: "SCR",  label: "SCR — South Central" },
  { code: "SWR",  label: "SWR — South Western" },
] as const;

export type ZoneCode = (typeof VALID_ZONES)[number]["code"];

export const ZONE_CODES = VALID_ZONES.map((z) => z.code) as readonly ZoneCode[];
