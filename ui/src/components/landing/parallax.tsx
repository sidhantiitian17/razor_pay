"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

/**
 * Landing-only scroll parallax.
 *
 * GSAP + ScrollTrigger drive layered yPercent motion, Lenis smooths the scroll.
 * Everything is opt-in per scene and every scroll-linked transform is skipped
 * entirely when the visitor asks for reduced motion — the layers then render in
 * their natural document position, fully visible and readable.
 */

/** Layer id -> yPercent travel. Higher = moves further with the scroll. */
const LAYER_TRAVEL: Record<string, number> = {
  "1": 40,
  "2": 26,
  "3": 14,
  "4": -10,
};

/** Smooth scrolling for the whole landing route; no-op under reduced motion. */
export function useLandingSmoothScroll(): void {
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    if (reduced || typeof window === "undefined") return;

    let disposed = false;
    let dispose: (() => void) | undefined;

    void (async () => {
      const [{ default: gsap }, { ScrollTrigger }, { default: Lenis }] = await Promise.all([
        import("gsap"),
        import("gsap/ScrollTrigger"),
        import("@studio-freight/lenis"),
      ]);
      if (disposed) return;

      gsap.registerPlugin(ScrollTrigger);
      const lenis = new Lenis();
      const update = () => ScrollTrigger.update();
      const raf = (time: number) => lenis.raf(time * 1000);

      lenis.on("scroll", update);
      gsap.ticker.add(raf);
      gsap.ticker.lagSmoothing(0);

      dispose = () => {
        gsap.ticker.remove(raf);
        gsap.ticker.lagSmoothing(500, 33);
        lenis.off("scroll", update);
        lenis.destroy();
      };
    })();

    return () => {
      disposed = true;
      dispose?.();
    };
  }, [reduced]);
}

/**
 * A parallax scene. Children marked with <ParallaxLayer layer="N"> move at
 * different speeds while the scene crosses the viewport.
 */
export function ParallaxScene({
  children,
  className,
  probe,
}: {
  children: ReactNode;
  className?: string | undefined;
  probe?: string | undefined;
}) {
  const reduced = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scene = ref.current;
    if (reduced || !scene || typeof window === "undefined") return;

    let disposed = false;
    let dispose: (() => void) | undefined;

    void (async () => {
      const [{ default: gsap }, { ScrollTrigger }] = await Promise.all([
        import("gsap"),
        import("gsap/ScrollTrigger"),
      ]);
      if (disposed) return;

      gsap.registerPlugin(ScrollTrigger);
      const layers = Array.from(scene.querySelectorAll<HTMLElement>("[data-parallax-layer]"));
      if (layers.length === 0) return;

      const timeline = gsap.timeline({
        scrollTrigger: {
          trigger: scene,
          start: "top bottom",
          end: "bottom top",
          scrub: true,
          invalidateOnRefresh: true,
        },
      });

      layers.forEach((layer, index) => {
        const key = layer.dataset["parallaxLayer"] ?? "1";
        timeline.fromTo(
          layer,
          { yPercent: 0 },
          { yPercent: LAYER_TRAVEL[key] ?? 0, ease: "none" },
          index === 0 ? undefined : "<",
        );
      });

      dispose = () => {
        timeline.scrollTrigger?.kill();
        timeline.kill();
        gsap.set(layers, { clearProps: "transform" });
      };
    })();

    return () => {
      disposed = true;
      dispose?.();
    };
  }, [reduced]);

  return (
    <div
      ref={ref}
      data-parallax-layers=""
      data-parallax-active={reduced ? "false" : "true"}
      data-motion-probe={probe}
      className={cn("relative", className)}
    >
      {children}
    </div>
  );
}

export function ParallaxLayer({
  layer,
  children,
  className,
}: {
  layer: "1" | "2" | "3" | "4";
  children: ReactNode;
  className?: string | undefined;
}) {
  return (
    <div data-parallax-layer={layer} className={cn("will-change-transform", className)}>
      {children}
    </div>
  );
}
