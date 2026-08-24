import type { ExceptionRow } from "@/lib/use-exceptions";

const HEADERS = [
  "exception_id",
  "run_id",
  "bucket",
  "severity",
  "status",
  "assignee",
  "proposed_action",
  "row_id_count",
  "row_ids",
  "evidence",
  "resolution_note",
] as const;

/** RFC 4180: every field quoted, embedded quotes doubled. */
function quote(value: string | number | null): string {
  const text = value === null ? "" : String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

export function exceptionsToCsv(rows: ExceptionRow[]): string {
  const lines = [HEADERS.map((h) => quote(h)).join(",")];

  for (const row of rows) {
    lines.push(
      [
        quote(row.exception_id),
        quote(row.run_id),
        quote(row.bucket),
        quote(row.severity),
        quote(row.status),
        quote(row.assignee),
        quote(row.proposed_action),
        quote(row.row_ids.length),
        quote(row.row_ids.join(";")),
        quote(row.evidence.join(";")),
        quote(row.resolution_note),
      ].join(","),
    );
  }

  return `${lines.join("\r\n")}\r\n`;
}

export function downloadCsv(filename: string, contents: string): void {
  const blob = new Blob([contents], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
