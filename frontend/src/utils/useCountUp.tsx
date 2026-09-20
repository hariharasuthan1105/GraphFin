import React, { useState, useEffect, useRef } from "react";

export function useCountUp(
  targetValue: number | undefined | null,
  duration = 400,
  decimals = 0
): number {
  const [displayValue, setDisplayValue] = useState<number>(() => targetValue ?? 0);
  const prevValueRef = useRef<number>(targetValue ?? 0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    if (targetValue === undefined || targetValue === null || isNaN(targetValue)) {
      return;
    }

    const startVal = prevValueRef.current;
    const endVal = targetValue;

    if (startVal === endVal) {
      setDisplayValue(endVal);
      return;
    }

    const startTime = performance.now();

    const updateFrame = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Ease-out cubic curve
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = startVal + (endVal - startVal) * easeProgress;

      setDisplayValue(parseFloat(current.toFixed(decimals)));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(updateFrame);
      } else {
        prevValueRef.current = endVal;
        setDisplayValue(endVal);
      }
    };

    frameRef.current = requestAnimationFrame(updateFrame);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [targetValue, duration, decimals]);

  return displayValue;
}

export const AnimatedNumber: React.FC<{
  value: number | undefined | null;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}> = ({ value, duration = 400, decimals = 0, prefix = "", suffix = "", className = "" }) => {
  const animated = useCountUp(value, duration, decimals);
  if (value === undefined || value === null) {
    return <span className={className}>—</span>;
  }
  const formatted = decimals > 0 ? animated.toFixed(decimals) : Math.round(animated).toLocaleString();
  return (
    <span className={className}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
};
