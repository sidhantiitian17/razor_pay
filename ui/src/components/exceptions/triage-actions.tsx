import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { TriageAction } from "@/lib/use-triage";

export function TriageActions({
  assigneeLabel,
  pending,
  onAction,
}: {
  assigneeLabel: string | null;
  pending: boolean;
  onAction: (action: TriageAction) => void;
}) {
  const [note, setNote] = useState("");

  if (!assigneeLabel) {
    return (
      <div className="panel grid gap-2 p-3">
        <div className="label-micro">Triage</div>
        <p className="text-xs text-muted-foreground">Triage writes require a signed-in session.</p>
        <Link
          to="/auth"
          className="inline-flex w-fit items-center rounded border border-border bg-surface px-3 py-1.5 text-xs text-foreground transition-colors hover:border-border-strong"
        >
          Sign in to triage
        </Link>
      </div>
    );
  }

  return (
    <div className="panel grid gap-2 p-3">
      <div className="label-micro">Triage</div>
      <Textarea
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="Resolution note"
        rows={2}
        className="text-xs"
      />
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={pending}
          onClick={() => onAction({ kind: "assign", assignee: assigneeLabel })}
        >
          Assign to me
        </Button>
        <Button
          size="sm"
          disabled={pending || note.trim().length === 0}
          onClick={() => onAction({ kind: "resolve", note: note.trim() })}
        >
          Resolve with note
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={pending}
          onClick={() => onAction({ kind: "wont_fix", note: note.trim() })}
        >
          Won&apos;t fix
        </Button>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Writes touch only status, assignee and resolution_note, as {assigneeLabel}.
      </p>
    </div>
  );
}
