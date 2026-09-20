import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  className = "",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center justify-center font-sans font-medium rounded transition-colors focus:outline-none focus:ring-1 focus:ring-accent-primary disabled:opacity-50 disabled:cursor-not-allowed select-none";

  const sizeStyles = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
  };

  const variantStyles = {
    primary:
      "bg-accent-primary text-text-primary hover:bg-[#3478EB] active:bg-[#2566D8]",
    secondary:
      "bg-surface-raised text-text-primary border border-hairline hover:bg-[#232D3A] active:bg-[#1E2632]",
    danger:
      "bg-status-suspicious text-text-primary hover:bg-[#E03A43] active:bg-[#C82A33]",
    ghost:
      "bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface active:bg-surface-raised",
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          {/* Simple rotating 16px arc in accent-primary */}
          <svg
            className="animate-spin h-4 w-4 text-text-primary"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle
              cx="12"
              cy="12"
              r="9"
              stroke="#232B33"
              strokeWidth="2.5"
            />
            <path
              d="M12 3a9 9 0 0 1 9 9"
              stroke="#4589FF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
          <span className="text-text-secondary opacity-90">{children}</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
};
