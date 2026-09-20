import React from "react";
import { TaxBracketBreakdown, TaxRuleMetadata } from "../../types/tax";

interface TaxBracketVisualizerProps {
  ruleMetadata: TaxRuleMetadata | null;
  breakdown: TaxBracketBreakdown[];
  currencySymbol: string;
  taxableIncome: number;
}

export const TaxBracketVisualizer: React.FC<TaxBracketVisualizerProps> = ({
  ruleMetadata,
  breakdown,
  currencySymbol,
  taxableIncome,
}) => {
  if (!ruleMetadata && breakdown.length === 0) {
    return (
      <div className="bg-surface border border-hairline rounded-lg p-6 text-center text-xs font-mono text-text-tertiary">
        Select a jurisdiction to view tax bracket visualization.
      </div>
    );
  }

  // Use active calculation breakdown if available, else build from static rules
  const displayItems = breakdown.length > 0
    ? breakdown.map((b) => ({
        label: b.bracket_label,
        min: b.min_income,
        max: b.max_income,
        ratePercent: Math.round(b.rate * 100 * 100) / 100,
        taxableAmount: b.taxable_amount_in_bracket,
        taxAmount: b.tax_amount,
        isActive: b.taxable_amount_in_bracket > 0,
      }))
    : (ruleMetadata?.brackets || []).map((b) => {
        const taxableAmount = b.max === null
          ? Math.max(0, taxableIncome - b.min)
          : Math.max(0, Math.min(taxableIncome, b.max) - b.min);
        return {
          label: b.label,
          min: b.min,
          max: b.max,
          ratePercent: b.rate_percent,
          taxableAmount: taxableIncome > b.min ? taxableAmount : 0,
          taxAmount: (taxableAmount * b.rate_percent) / 100,
          isActive: taxableIncome > b.min,
        };
      });

  const maxRate = Math.max(...displayItems.map((item) => item.ratePercent), 30);

  return (
    <div className="bg-surface border border-hairline rounded-lg p-6 space-y-4 select-none">
      <div className="flex items-center justify-between border-b border-hairline pb-3">
        <div>
          <h3 className="text-sm font-medium font-sans text-text-primary">
            Progressive Tax Bracket Visualization
          </h3>
          <p className="text-xs font-mono text-text-tertiary mt-0.5">
            Backend Rule Engine Version: {ruleMetadata?.rule_version || "Dynamic"}
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs font-mono text-text-secondary">
            Currency: <span className="text-accent-primary font-bold">{currencySymbol}</span>
          </span>
        </div>
      </div>

      {/* Bracket list rendering */}
      <div className="space-y-3 pt-1">
        {displayItems.map((item, idx) => {
          const widthPercent = maxRate > 0 ? (item.ratePercent / maxRate) * 100 : 0;

          return (
            <div
              key={idx}
              className={`p-3 rounded-md border transition-all ${
                item.isActive
                  ? "bg-surface-raised/60 border-accent-primary/50 shadow-sm"
                  : "bg-surface/40 border-hairline opacity-60"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                <span className="font-sans text-text-primary font-medium">
                  {item.label}
                </span>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                    item.ratePercent === 0
                      ? "bg-surface-raised text-text-tertiary"
                      : "bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
                  }`}>
                    {item.ratePercent}%
                  </span>
                  {item.taxableAmount > 0 && (
                    <span className="text-text-secondary">
                      Taxable: <span className="text-text-primary font-bold">{currencySymbol}{item.taxableAmount.toLocaleString()}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Bar visualization */}
              <div className="w-full bg-canvas rounded-full h-2 overflow-hidden flex items-center">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    item.isActive
                      ? item.ratePercent === 0
                        ? "bg-status-normal/70"
                        : "bg-accent-primary"
                      : "bg-hairline"
                  }`}
                  style={{ width: `${Math.max(widthPercent, 4)}%` }}
                />
              </div>

              {/* Tax levied note */}
              {item.taxAmount > 0 && (
                <div className="mt-1.5 text-[11px] font-mono text-text-tertiary flex justify-end">
                  Bracket Tax: <span className="text-accent-primary ml-1">{currencySymbol}{item.taxAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Visual hierarchy breakdown tree */}
      <div className="pt-3 border-t border-hairline font-mono text-xs text-text-tertiary">
        <div className="text-[11px] uppercase tracking-wider text-text-tertiary mb-2 font-sans font-semibold">
          Progressive Marginal Slab Hierarchy
        </div>
        <div className="bg-canvas p-3 rounded border border-hairline space-y-1">
          <div>Taxable Income: {currencySymbol}{taxableIncome.toLocaleString()}</div>
          <div className="pl-2 border-l border-hairline space-y-1">
            {displayItems.map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-text-tertiary">├──</span>
                <span className={item.isActive ? "text-accent-primary font-medium" : "text-text-tertiary"}>
                  {item.ratePercent}% Bracket: {item.taxableAmount > 0 ? `${currencySymbol}${item.taxableAmount.toLocaleString()} taxable` : "No income in band"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
