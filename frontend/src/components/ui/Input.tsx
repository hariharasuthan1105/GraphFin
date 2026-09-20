import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  mono?: boolean;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  mono = false,
  error,
  helperText,
  className = "",
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="flex flex-col gap-1 text-left">
      {label && (
        <label
          htmlFor={inputId}
          className="text-xs font-sans text-text-secondary select-none"
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`bg-surface border ${
          error ? "border-status-suspicious" : "border-hairline"
        } rounded px-3 py-1.5 text-sm text-text-primary ${
          mono ? "font-mono" : "font-sans"
        } placeholder:text-text-tertiary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary transition-colors disabled:opacity-50 disabled:bg-canvas ${className}`}
        {...props}
      />
      {error && <span className="text-xs text-status-suspicious font-sans">{error}</span>}
      {helperText && !error && (
        <span className="text-xs text-text-tertiary font-sans">{helperText}</span>
      )}
    </div>
  );
};
