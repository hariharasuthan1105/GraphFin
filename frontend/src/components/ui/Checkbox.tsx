import React from "react";

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  description?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  label,
  description,
  id,
  className = "",
  ...props
}) => {
  const checkboxId = id || `check-${label.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <label
      htmlFor={checkboxId}
      className="flex items-start gap-2.5 cursor-pointer select-none group text-left"
    >
      <input
        type="checkbox"
        id={checkboxId}
        className={`mt-0.5 h-4 w-4 rounded border border-hairline bg-surface text-accent-primary focus:ring-1 focus:ring-accent-primary focus:ring-offset-0 focus:outline-none cursor-pointer accent-[#4589FF] ${className}`}
        {...props}
      />
      <div className="flex flex-col">
        <span className="text-sm font-sans text-text-primary group-hover:text-text-primary">
          {label}
        </span>
        {description && (
          <span className="text-xs font-sans text-text-tertiary">
            {description}
          </span>
        )}
      </div>
    </label>
  );
};
