import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useRef } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ExceptionRow } from "@/lib/use-exceptions";

const SEVERITY_TONE: Record<string, string> = {
  high: "text-destructive",
  medium: "text-warning",
  low: "text-muted-foreground",
};

const ROW_HEIGHT = 40;

export function ExceptionTable({
  rows,
  selectedId,
  onSelect,
}: {
  rows: ExceptionRow[];
  selectedId: string | null;
  onSelect: (row: ExceptionRow) => void;
}) {
  const reduced = usePrefersReducedMotion();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const columns = useMemo<ColumnDef<ExceptionRow>[]>(
    () => [
      {
        id: "exception_id",
        header: "Exception",
        accessorFn: (row) => row.exception_id,
        cell: (ctx) => <span className="tnum">{ctx.row.original.exception_id}</span>,
      },
      {
        id: "bucket",
        header: "Bucket",
        accessorFn: (row) => row.bucket,
      },
      {
        id: "severity",
        header: "Severity",
        accessorFn: (row) => row.severity,
        cell: (ctx) => (
          <span className={cn("font-medium", SEVERITY_TONE[ctx.row.original.severity])}>
            {ctx.row.original.severity}
          </span>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorFn: (row) => row.status,
      },
      {
        id: "assignee",
        header: "Assignee",
        accessorFn: (row) => row.assignee ?? "—",
      },
      {
        id: "row_ids",
        header: "Rows",
        accessorFn: (row) => row.row_ids.length,
        cell: (ctx) => <span className="tnum">{formatCount(ctx.row.original.row_ids.length)}</span>,
      },
      {
        id: "proposed_action",
        header: "Proposed action",
        accessorFn: (row) => row.proposed_action,
      },
    ],
    [],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getRowId: (row) => row.exception_id,
    getCoreRowModel: getCoreRowModel(),
  });

  const tableRows = table.getRowModel().rows;

  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  const items = virtualizer.getVirtualItems();

  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <div className="min-w-[64rem]">
          <div className="grid grid-cols-[1.2fr_1fr_0.7fr_0.8fr_1.2fr_0.5fr_1.6fr] gap-2 border-b border-border bg-surface px-3 py-2">
            {table.getHeaderGroups()[0]?.headers.map((header) => (
              <div key={header.id} className="label-micro truncate">
                {flexRender(header.column.columnDef.header, header.getContext())}
              </div>
            ))}
          </div>

          <div ref={scrollRef} className="max-h-[28rem] overflow-auto" role="grid">
            <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
              <AnimatePresence initial={false}>
                {items.map((item) => {
                  const row = tableRows[item.index];
                  if (!row) return null;
                  const isSelected = row.original.exception_id === selectedId;

                  return (
                    <motion.div
                      key={row.id}
                      layout={reduced ? false : "position"}
                      initial={reduced ? false : { opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={reduced ? { opacity: 1 } : { opacity: 0, x: -12 }}
                      transition={{ duration: reduced ? 0 : 0.18 }}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: `${item.size}px`,
                        transform: `translateY(${item.start}px)`,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => onSelect(row.original)}
                        className={cn(
                          "grid h-full w-full grid-cols-[1.2fr_1fr_0.7fr_0.8fr_1.2fr_0.5fr_1.6fr] items-center gap-2 border-b border-border/60 px-3 text-left text-xs transition-colors hover:bg-surface",
                          isSelected && "bg-surface",
                        )}
                      >
                        {row.getVisibleCells().map((cell) => (
                          <div key={cell.id} className="truncate text-foreground">
                            {flexRender(cell.column.columnDef.cell, cell.getContext()) ??
                              String(cell.getValue() ?? "")}
                          </div>
                        ))}
                      </button>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
