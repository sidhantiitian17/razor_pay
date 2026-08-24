import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { supabase } from "@/integrations/supabase/client";
import { exceptionsQueryKey, type ExceptionRow } from "@/lib/use-exceptions";

export type TriageAction =
  | { kind: "assign"; assignee: string }
  | { kind: "resolve"; note: string }
  | { kind: "wont_fix"; note: string };

export interface TriageInput {
  exceptionId: string;
  action: TriageAction;
}

/** Only status / assignee / resolution_note are writable, and only when signed in. */
function patchFor(action: TriageAction): Partial<ExceptionRow> {
  if (action.kind === "assign") {
    return { status: "assigned", assignee: action.assignee };
  }
  if (action.kind === "resolve") {
    return { status: "resolved", resolution_note: action.note };
  }
  return { status: "wont_fix", resolution_note: action.note };
}

export function useTriage(runId: string | undefined) {
  const queryClient = useQueryClient();
  const key = exceptionsQueryKey(runId);

  return useMutation({
    mutationFn: async ({ exceptionId, action }: TriageInput) => {
      const { error } = await supabase
        .from("exceptions")
        .update(patchFor(action))
        .eq("exception_id", exceptionId);
      if (error) throw new Error(error.message);
      return { exceptionId };
    },
    onMutate: async ({ exceptionId, action }: TriageInput) => {
      await queryClient.cancelQueries({ queryKey: key });
      const snapshot = queryClient.getQueryData<ExceptionRow[]>(key);

      if (snapshot) {
        const patch = patchFor(action);
        queryClient.setQueryData<ExceptionRow[]>(
          key,
          snapshot.map((row) => (row.exception_id === exceptionId ? { ...row, ...patch } : row)),
        );
      }

      return { snapshot };
    },
    onError: (error, _input, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData<ExceptionRow[]>(key, context.snapshot);
      }
      toast.error("Triage update failed", {
        description: error instanceof Error ? error.message : "The row was rolled back.",
      });
    },
    onSuccess: () => {
      toast.success("Triage recorded");
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: key });
    },
  });
}
