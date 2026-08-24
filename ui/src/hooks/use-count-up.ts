import { useEffect, useRef, useState } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";

/**
 * Count-up driven entirely by a real fetched value: the animation only
 * interpolates towards `target` and always settles exactly on it. With reduced
 * motion the target is returned immediately.
 */
export function useCountUp(target: number, durationMs = 650): number {
  const reduced = usePrefersReducedMotion();
  const [value, setValue] = useState(target);
  const fromRef = useRef(target);

  useEffect(() => {
    if (reduced || durationMs <= 0) {
      fromRef.current = target;
      setValue(target);
      return;
    }

    const from = fromRef.current;
    if (from === target) {
      setValue(target);
      return;
    }

    let frame = 0;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(from + (target - from) * eased);
      if (t < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
        setValue(target);
      }
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs, reduced]);

  return value;
}
