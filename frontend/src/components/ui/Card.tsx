import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "surface" | "surface-raised";
  noBorder?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = "surface",
  noBorder = false,
  className = "",
  ...props
}) => {
  const bg = variant === "surface" ? "bg-surface" : "bg-surface-raised";
  const border = noBorder ? "" : "border border-hairline";

  return (
    <div
      className={`${bg} ${border} rounded p-5 text-left transition-colors ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
