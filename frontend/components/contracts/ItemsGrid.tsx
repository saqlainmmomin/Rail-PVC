"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  type ColDef,
} from "ag-grid-community";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api/client";

ModuleRegistry.registerModules([AllCommunityModule]);

const gridTheme = themeQuartz.withParams({
  fontSize: 13,
  headerHeight: 36,
  rowHeight: 34,
});

type SteelSubtype = "angles" | "plates" | "other_sections" | "tmt" | null;

interface ContractItem {
  id?: string;
  item_code: string;
  description: string;
  unit: string;
  original_qty: number | string | null;
  revised_qty: number | string | null;
  base_rate: number | string | null;
  agreement_rate: number | string | null;
  is_cement_item: boolean;
  steel_subtype: SteelSubtype;
}

type RowState = ContractItem & {
  _isNew?: boolean;
  _dirty?: boolean;
};

function emptyRow(): RowState {
  return {
    item_code: "",
    description: "",
    unit: "",
    original_qty: null,
    revised_qty: null,
    base_rate: null,
    agreement_rate: null,
    is_cement_item: false,
    steel_subtype: null,
    _isNew: true,
    _dirty: true,
  };
}

export function ItemsGrid({ scheduleId }: { scheduleId: string }) {
  const queryClient = useQueryClient();
  const itemsQuery = useQuery<ContractItem[]>({
    queryKey: ["schedule-items", scheduleId],
    queryFn: () =>
      apiFetch<ContractItem[]>(`/api/schedules/${scheduleId}/items`),
  });

  const [rows, setRows] = useState<RowState[]>([]);
  const [saveProgress, setSaveProgress] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const gridRef = useRef<AgGridReact<RowState>>(null);

  useEffect(() => {
    if (itemsQuery.data) {
      setRows(itemsQuery.data.map((r) => ({ ...r })));
      setSaveProgress(null);
      setSaveError(null);
    }
  }, [itemsQuery.data]);

  const cementSteelConflicts = useMemo(
    () => rows.filter((r) => r.is_cement_item && r.steel_subtype),
    [rows],
  );

  const columnDefs = useMemo<ColDef<RowState>[]>(
    () => [
      { field: "item_code", headerName: "Code", editable: true, width: 110 },
      { field: "description", headerName: "Description", editable: true, flex: 2 },
      { field: "unit", headerName: "Unit", editable: true, width: 80 },
      {
        field: "original_qty",
        headerName: "Orig qty",
        editable: true,
        width: 110,
        cellDataType: "number",
      },
      {
        field: "revised_qty",
        headerName: "Rev qty",
        editable: true,
        width: 110,
        cellDataType: "number",
      },
      {
        field: "base_rate",
        headerName: "Base rate",
        editable: true,
        width: 120,
        cellDataType: "number",
      },
      {
        field: "agreement_rate",
        headerName: "Agreement rate",
        editable: true,
        width: 140,
        cellDataType: "number",
      },
      {
        field: "is_cement_item",
        headerName: "Cement?",
        editable: true,
        width: 90,
        cellDataType: "boolean",
      },
      {
        field: "steel_subtype",
        headerName: "Steel subtype",
        editable: true,
        width: 150,
        cellEditor: "agSelectCellEditor",
        cellEditorParams: {
          values: ["—", "angles", "plates", "other_sections", "tmt"],
        },
        valueParser: (p) => (p.newValue === "—" ? null : p.newValue),
        valueFormatter: (p) => p.value ?? "—",
      },
    ],
    [],
  );

  function addRow() {
    setRows((prev) => [...prev, emptyRow()]);
  }

  async function saveAll() {
    setSaveError(null);
    const dirty = rows
      .map((r, i) => ({ r, i }))
      .filter(({ r }) => r._isNew || r._dirty);
    if (dirty.length === 0) {
      setSaveProgress("Nothing to save.");
      return;
    }
    let n = 0;
    for (const { r, i } of dirty) {
      n += 1;
      setSaveProgress(`Saving ${n} of ${dirty.length}…`);
      try {
        await apiFetch(`/api/schedules/${scheduleId}/items`, {
          method: "POST",
          body: {
            item_code: r.item_code,
            description: r.description,
            unit: r.unit,
            original_qty: r.original_qty,
            revised_qty: r.revised_qty,
            base_rate: r.base_rate,
            agreement_rate: r.agreement_rate,
            is_cement_item: r.is_cement_item,
            steel_subtype: r.steel_subtype,
          },
        });
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? `Row ${i + 1} (${r.item_code || "<no code>"}): ${err.message}`
            : `Row ${i + 1}: save failed`;
        setSaveError(msg);
        setSaveProgress(null);
        return;
      }
    }
    setSaveProgress(`Saved ${dirty.length} row(s).`);
    queryClient.invalidateQueries({ queryKey: ["schedule-items", scheduleId] });
  }

  return (
    <div className="space-y-3">
      {cementSteelConflicts.length > 0 && (
        <div className="text-[12px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          {cementSteelConflicts.length} row(s) marked as both cement AND a steel
          subtype. The engine treats these as mutually exclusive buckets —
          clear one before saving.
        </div>
      )}

      <div style={{ height: 480, width: "100%" }}>
        <AgGridReact<RowState>
          ref={gridRef}
          theme={gridTheme}
          rowData={rows}
          columnDefs={columnDefs}
          defaultColDef={{ resizable: true, sortable: true }}
          singleClickEdit
          stopEditingWhenCellsLoseFocus
          onCellValueChanged={(e) => {
            const updated = [...rows];
            const idx = e.rowIndex;
            if (idx === null) return;
            updated[idx] = { ...updated[idx], _dirty: true };
            setRows(updated);
          }}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="button" variant="secondary" size="sm" onClick={addRow}>
          + Add row
        </Button>
        <Button type="button" variant="primary" size="sm" onClick={saveAll}>
          Save all
        </Button>
        {saveProgress && (
          <span className="text-[12px] text-slate-500">{saveProgress}</span>
        )}
        {saveError && (
          <span className="text-[12px] text-red-600">{saveError}</span>
        )}
      </div>
    </div>
  );
}
