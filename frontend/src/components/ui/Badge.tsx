import React from "react";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: "neutral" | "suspicious" | "normal" | "warning" | "accent";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  className = "",
}) => {
  const variantStyles = {
    neutral: "bg-surface-raised text-text-secondary border border-hairline",
    suspicious: "bg-[#2D1619] text-status-suspicious border border-[#521A1F]",
    normal: "bg-[#12281B] text-status-normal border border-[#1B4D2B]",
    warning: "bg-[#2B230B] text-status-warning border border-[#4F3F12]",
    accent: "bg-[#102445] text-accent-primary border border-[#1C3E75]",
  };

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 text-xs font-mono rounded-sm ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
};
