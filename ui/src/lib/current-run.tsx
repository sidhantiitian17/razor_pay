import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * The run every route reads from. Selecting a run in the header changes the
 * whole panel; with nothing selected each route falls back to the newest run
 * in the database. The identity always comes from fetched rows — never a
 * hardcoded run id.
 */
interface CurrentRunValue {
  /** Explicitly selected run id, or null when following the newest run. */
  selectedRunId: string | null;
  selectRun: (runId: string | null) => void;
}

const CurrentRunContext = createContext<CurrentRunValue>({
  selectedRunId: null,
  selectRun: () => {},
});

const STORAGE_KEY = "recon.selected-run";

export function CurrentRunProvider({ children }: { children: ReactNode }) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Restore the selection after hydration so a reload keeps pointing the whole
  // panel at the same run. Read in an effect, never in the state initializer.
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) setSelectedRunId(stored);
    } catch {
      /* storage unavailable */
    }
  }, []);

  const selectRun = useCallback((runId: string | null) => {
    setSelectedRunId(runId);
    try {
      if (runId) window.localStorage.setItem(STORAGE_KEY, runId);
      else window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* storage unavailable — selection stays in-memory only */
    }
  }, []);

  const value = useMemo<CurrentRunValue>(
    () => ({ selectedRunId, selectRun }),
    [selectedRunId, selectRun],
  );

  return <CurrentRunContext.Provider value={value}>{children}</CurrentRunContext.Provider>;
}

export function useCurrentRun(): CurrentRunValue {
  return useContext(CurrentRunContext);
}
