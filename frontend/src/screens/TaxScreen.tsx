import React, { useState, useEffect } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import {
  JurisdictionInfo,
  TaxCalculationRequest,
  TaxCalculationResponse,
  TaxRuleMetadata,
} from "../types/tax";
import { TaxBracketVisualizer } from "../components/tax/TaxBracketVisualizer";

export const TaxScreen: React.FC = () => {
  const { datasetCurrency } = useApp();

  // State
  const [jurisdictions, setJurisdictions] = useState<JurisdictionInfo[]>([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>("IN");
  const [selectedTaxYear, setSelectedTaxYear] = useState<string>("AY 2026–27");
  const [incomeInput, setIncomeInput] = useState<string>("1500000");
  const [incomeType, setIncomeType] = useState<"taxable" | "gross">("taxable");
  const [filingStatus, setFilingStatus] = useState<string>("single");
  const [region, setRegion] = useState<string>("england");
  const [deductions, setDeductions] = useState<string>("0");
  const [churchTax, setChurchTax] = useState<boolean>(false);
  const [parts, setParts] = useState<number>(1.0);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TaxCalculationResponse | null>(null);
  const [ruleMetadata, setRuleMetadata] = useState<TaxRuleMetadata | null>(null);

  // Fetch supported jurisdictions on mount
  useEffect(() => {
    api
      .getTaxJurisdictions()
      .then((data) => {
        setJurisdictions(data);
        if (data.length > 0) {
          const defaultIn = data.find((j) => j.id === "IN") || data[0];
          setSelectedJurisdiction(defaultIn.id);
          setSelectedTaxYear(defaultIn.supported_years[0]);
        }
      })
      .catch((err) => {
        setError(err?.message || "Failed to load tax jurisdictions from backend.");
      });
  }, []);

  // Fetch rule metadata whenever jurisdiction or year changes
  useEffect(() => {
    if (!selectedJurisdiction || !selectedTaxYear) return;

    api
      .getTaxRules(selectedJurisdiction, selectedTaxYear)
      .then((meta) => {
        setRuleMetadata(meta);
      })
      .catch(() => {
        setRuleMetadata(null);
      });
  }, [selectedJurisdiction, selectedTaxYear]);

  // Handle Jurisdiction Selection change
  const handleJurisdictionChange = (code: string) => {
    setSelectedJurisdiction(code);
    const found = jurisdictions.find((j) => j.id === code);
    if (found && found.supported_years.length > 0) {
      setSelectedTaxYear(found.supported_years[0]);
    }
    // Set appropriate default income amount for jurisdiction demo
    if (code === "IN") setIncomeInput("1500000");
    else if (code === "US") setIncomeInput("100000");
    else if (code === "GB") setIncomeInput("80000");
    else if (code === "DE") setIncomeInput("60000");
    else if (code === "FR") setIncomeInput("60000");

    setResult(null);
  };

  // Perform tax calculation API call
  const handleCalculate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);

    const val = parseFloat(incomeInput.replace(/,/g, "")) || 0;
    const ded = parseFloat(deductions.replace(/,/g, "")) || 0;

    const payload: TaxCalculationRequest = {
      jurisdiction: selectedJurisdiction,
      tax_year: selectedTaxYear,
      deductions: ded,
      filing_status: selectedJurisdiction === "US" ? filingStatus : undefined,
      region: selectedJurisdiction === "GB" ? region : undefined,
      church_tax: selectedJurisdiction === "DE" ? churchTax : undefined,
      parts: selectedJurisdiction === "FR" ? parts : undefined,
    };

    if (incomeType === "gross") {
      payload.gross_income = val;
    } else {
      payload.taxable_income = val;
    }

    try {
      const res = await api.calculateTax(payload);
      setResult(res);
    } catch (err: any) {
      setError(err?.message || "Tax calculation failed.");
    } finally {
      setLoading(false);
    }
  };

  // Initial calculation trigger
  useEffect(() => {
    if (selectedJurisdiction) {
      handleCalculate();
    }
  }, [selectedJurisdiction, selectedTaxYear]);

  const activeJurisdictionInfo = jurisdictions.find((j) => j.id === selectedJurisdiction);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12 font-sans select-none">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-hairline pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Tax Analytics
            </h1>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-accent-primary/10 text-accent-primary border border-accent-primary/30">
              Multi-Jurisdiction Module
            </span>
          </div>
          <p className="text-xs font-mono text-text-tertiary mt-1">
            Deterministic progressive income tax estimation for India, United States, United Kingdom, Germany, and France.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-surface-raised/60 px-3.5 py-2 rounded-lg border border-hairline text-xs font-mono text-text-secondary">
          <span className="w-2 h-2 rounded-full bg-status-normal animate-pulse" />
          <span>Additive Layer — Independent of Anomaly Engine</span>
        </div>
      </div>

      {/* Main Calculation Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Inputs Form (5 cols) */}
        <div className="lg:col-span-5 bg-surface border border-hairline rounded-xl p-6 space-y-5">
          <div className="border-b border-hairline pb-3">
            <h2 className="text-base font-semibold text-text-primary">
              Tax Parameters
            </h2>
            <p className="text-xs text-text-tertiary font-mono">
              Configure jurisdiction, year, and explicit income inputs.
            </p>
          </div>

          <form onSubmit={handleCalculate} className="space-y-4">
            {/* Jurisdiction Dropdown */}
            <div>
              <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                Jurisdiction
              </label>
              <select
                value={selectedJurisdiction}
                onChange={(e) => handleJurisdictionChange(e.target.value)}
                className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm text-text-primary font-sans focus:outline-none focus:border-accent-primary transition-colors"
              >
                {jurisdictions.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.name} ({j.currency_symbol} {j.currency})
                  </option>
                ))}
              </select>
            </div>

            {/* Tax Year Dropdown */}
            <div>
              <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                Tax Year / Assessment Year
              </label>
              <select
                value={selectedTaxYear}
                onChange={(e) => setSelectedTaxYear(e.target.value)}
                className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm text-text-primary font-sans focus:outline-none focus:border-accent-primary transition-colors"
              >
                {activeJurisdictionInfo?.supported_years.map((yr) => (
                  <option key={yr} value={yr}>
                    {yr}
                  </option>
                ))}
              </select>
            </div>

            {/* Income Type & Input */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-mono font-medium text-text-secondary">
                  Income Amount ({activeJurisdictionInfo?.currency_symbol || "$"})
                </label>
                <div className="flex items-center gap-2 text-xs font-mono">
                  <button
                    type="button"
                    onClick={() => setIncomeType("taxable")}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      incomeType === "taxable"
                        ? "bg-accent-primary/20 text-accent-primary font-bold"
                        : "text-text-tertiary hover:text-text-secondary"
                    }`}
                  >
                    Taxable
                  </button>
                  <button
                    type="button"
                    onClick={() => setIncomeType("gross")}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      incomeType === "gross"
                        ? "bg-accent-primary/20 text-accent-primary font-bold"
                        : "text-text-tertiary hover:text-text-secondary"
                    }`}
                  >
                    Gross
                  </button>
                </div>
              </div>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-text-tertiary font-mono text-sm">
                  {activeJurisdictionInfo?.currency_symbol || "$"}
                </span>
                <input
                  type="text"
                  value={incomeInput}
                  onChange={(e) => setIncomeInput(e.target.value)}
                  className="w-full bg-canvas border border-hairline rounded-md pl-8 pr-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-primary transition-colors"
                  placeholder="e.g. 1500000"
                />
              </div>
            </div>

            {/* US Specific Option: Filing Status */}
            {selectedJurisdiction === "US" && (
              <div>
                <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                  Filing Status
                </label>
                <select
                  value={filingStatus}
                  onChange={(e) => setFilingStatus(e.target.value)}
                  className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm text-text-primary font-sans focus:outline-none focus:border-accent-primary"
                >
                  <option value="single">Single ($16,100 Std Deduction)</option>
                  <option value="married_joint">Married Filing Jointly ($32,200 Std Deduction)</option>
                  <option value="married_separate">Married Filing Separately ($16,100 Std Deduction)</option>
                  <option value="head_of_household">Head of Household ($24,150 Std Deduction)</option>
                </select>
              </div>
            )}

            {/* UK Specific Option: Region */}
            {selectedJurisdiction === "GB" && (
              <div>
                <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                  UK Region
                </label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm text-text-primary font-sans focus:outline-none focus:border-accent-primary"
                >
                  <option value="england">England / Wales / Northern Ireland</option>
                  <option value="scotland">Scotland (Scottish Income Tax)</option>
                </select>
              </div>
            )}

            {/* Germany Specific Option: Church Tax */}
            {selectedJurisdiction === "DE" && (
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="churchTax"
                  checked={churchTax}
                  onChange={(e) => setChurchTax(e.target.checked)}
                  className="rounded border-hairline bg-canvas text-accent-primary focus:ring-0"
                />
                <label htmlFor="churchTax" className="text-xs font-sans text-text-secondary cursor-pointer">
                  Church Tax Applicable (Kirchensteuer 8%/9%)
                </label>
              </div>
            )}

            {/* France Specific Option: Quotient Familial Parts */}
            {selectedJurisdiction === "FR" && (
              <div>
                <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                  Quotient Familial (Parts)
                </label>
                <input
                  type="number"
                  min="1"
                  step="0.5"
                  value={parts}
                  onChange={(e) => setParts(parseFloat(e.target.value) || 1.0)}
                  className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-primary"
                />
              </div>
            )}

            {/* Deductions input */}
            <div>
              <label className="block text-xs font-mono font-medium text-text-secondary mb-1.5">
                Additional Deductions / Exemptions
              </label>
              <input
                type="text"
                value={deductions}
                onChange={(e) => setDeductions(e.target.value)}
                className="w-full bg-canvas border border-hairline rounded-md px-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-primary transition-colors"
                placeholder="0"
              />
            </div>

            {/* Calculate Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-accent-primary hover:bg-accent-primary/90 text-canvas font-semibold py-2.5 px-4 rounded-md text-sm transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-canvas border-t-transparent rounded-full animate-spin" />
                  <span>Calculating...</span>
                </>
              ) : (
                <span>Calculate Tax Estimate</span>
              )}
            </button>
          </form>

          {/* Official Source Badge */}
          {ruleMetadata && (
            <div className="pt-4 border-t border-hairline text-xs font-mono text-text-tertiary space-y-1">
              <div>
                Source: <span className="text-text-secondary font-sans">{ruleMetadata.source}</span>
              </div>
              <div>
                URL:{" "}
                <a
                  href={ruleMetadata.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent-primary underline hover:text-accent-primary/80"
                >
                  {ruleMetadata.source_url}
                </a>
              </div>
              <div>Rule Version: {ruleMetadata.rule_version}</div>
            </div>
          )}
        </div>

        {/* Right Column: Output Metrics & Visualization (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {error && (
            <div className="bg-[#2D1619] border border-[#521A1F] p-4 rounded-xl text-status-suspicious text-sm font-sans">
              <span className="font-bold">Error:</span> {error}
            </div>
          )}

          {result && (
            <>
              {/* Key Summary Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-surface border border-hairline p-4 rounded-xl">
                  <div className="text-[11px] font-mono text-text-tertiary uppercase">
                    Taxable Income
                  </div>
                  <div className="text-lg font-bold font-mono text-text-primary mt-1">
                    {result.currency_symbol}
                    {result.taxable_income.toLocaleString()}
                  </div>
                </div>

                <div className="bg-surface border border-hairline p-4 rounded-xl">
                  <div className="text-[11px] font-mono text-text-tertiary uppercase">
                    Estimated Tax
                  </div>
                  <div className="text-lg font-bold font-mono text-accent-primary mt-1">
                    {result.currency_symbol}
                    {result.estimated_tax.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="bg-surface border border-hairline p-4 rounded-xl">
                  <div className="text-[11px] font-mono text-text-tertiary uppercase">
                    Effective Rate
                  </div>
                  <div className="text-lg font-bold font-mono text-text-primary mt-1">
                    {result.effective_tax_rate}%
                  </div>
                </div>

                <div className="bg-surface border border-hairline p-4 rounded-xl">
                  <div className="text-[11px] font-mono text-text-tertiary uppercase">
                    Marginal Rate
                  </div>
                  <div className="text-lg font-bold font-mono text-text-primary mt-1">
                    {result.marginal_tax_rate}%
                  </div>
                </div>
              </div>

              {/* Detailed Breakdown Table */}
              <div className="bg-surface border border-hairline rounded-xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-hairline pb-3">
                  <h3 className="text-sm font-semibold text-text-primary font-sans">
                    {result.country} — Tax Breakdown
                  </h3>
                  <span className="text-xs font-mono text-text-tertiary">
                    {result.rule_version}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-xs">
                    <thead>
                      <tr className="border-b border-hairline text-text-tertiary">
                        <th className="pb-2 font-medium">Bracket</th>
                        <th className="pb-2 font-medium text-right">Taxable Amount</th>
                        <th className="pb-2 font-medium text-right">Rate</th>
                        <th className="pb-2 font-medium text-right">Tax</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline">
                      {result.breakdown.map((row, idx) => (
                        <tr key={idx} className={row.taxable_amount_in_bracket > 0 ? "text-text-primary" : "text-text-tertiary opacity-60"}>
                          <td className="py-2.5 font-sans">{row.bracket_label}</td>
                          <td className="py-2.5 text-right">
                            {result.currency_symbol}
                            {row.taxable_amount_in_bracket.toLocaleString()}
                          </td>
                          <td className="py-2.5 text-right font-bold">
                            {(row.rate * 100).toFixed(1)}%
                          </td>
                          <td className="py-2.5 text-right text-accent-primary font-bold">
                            {result.currency_symbol}
                            {row.tax_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Adjustments & Reliefs Summary */}
                <div className="bg-canvas p-4 rounded-lg border border-hairline space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between text-text-secondary">
                    <span>Base Tax before reliefs:</span>
                    <span>{result.currency_symbol}{result.tax_before_reliefs.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>

                  {result.reliefs > 0 && (
                    <div className="flex justify-between text-status-normal font-semibold">
                      <span>Tax Rebate / Relief (e.g. Sec 87A):</span>
                      <span>-{result.currency_symbol}{result.reliefs.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                  )}

                  {result.surcharge > 0 && (
                    <div className="flex justify-between text-status-suspicious font-semibold">
                      <span>High Income Surcharge:</span>
                      <span>+{result.currency_symbol}{result.surcharge.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                  )}

                  {result.cess_or_additional_tax > 0 && (
                    <div className="flex justify-between text-text-secondary">
                      <span>Cess / Additional Tax:</span>
                      <span>+{result.currency_symbol}{result.cess_or_additional_tax.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                  )}

                  {result.church_tax > 0 && (
                    <div className="flex justify-between text-text-secondary">
                      <span>Church Tax (Kirchensteuer):</span>
                      <span>+{result.currency_symbol}{result.church_tax.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                  )}

                  <div className="flex justify-between border-t border-hairline pt-2 text-sm font-bold text-text-primary font-sans">
                    <span>Total Estimated Liability:</span>
                    <span className="text-accent-primary">
                      {result.currency_symbol}{result.estimated_tax.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Bracket Visualizer Component */}
          <TaxBracketVisualizer
            ruleMetadata={ruleMetadata}
            breakdown={result?.breakdown || []}
            currencySymbol={result?.currency_symbol || activeJurisdictionInfo?.currency_symbol || "$"}
            taxableIncome={result?.taxable_income || (parseFloat(incomeInput.replace(/,/g, "")) || 0)}
          />
        </div>
      </div>

      {/* Transaction & Anomaly Integration Context Notice */}
      <div className="bg-surface border border-hairline rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-status-warning" />
          <h3 className="text-sm font-bold text-text-primary font-sans">
            Transaction Activity vs. Tax Analytics Boundary
          </h3>
        </div>

        <p className="text-xs font-mono text-text-secondary leading-relaxed">
          GraphFin enforces a strict separation between <strong>transaction volume analytics</strong> and <strong>tax estimation</strong>.
          A transaction between two accounts is NOT automatically income. Tax analytics operate exclusively from explicitly classified income inputs.
        </p>

        {/* Example Contextual Entity Matrix */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-4 bg-canvas p-4 rounded-lg border border-hairline font-mono text-xs">
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Entity</span>
            <span className="text-text-primary font-bold">ACC019</span>
          </div>
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Transaction Activity</span>
            <span className="text-text-primary font-bold">{datasetCurrency === "INR" ? "₹" : "$"}8,40,000</span>
          </div>
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Anomaly Score</span>
            <span className="text-status-suspicious font-bold">High (0.842)</span>
          </div>
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Taxable Income</span>
            <span className="text-status-warning font-bold">Not classified</span>
          </div>
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Tax Estimate</span>
            <span className="text-text-tertiary italic">Unavailable</span>
          </div>
        </div>
      </div>

      {/* Mandatory Legal & Tax Disclaimer */}
      <div className="bg-surface-raised/40 border border-hairline rounded-xl p-5 text-xs font-mono text-text-tertiary space-y-2">
        <div className="font-bold text-text-secondary uppercase tracking-wider font-sans text-[11px]">
          Mandatory Regulatory Disclaimer
        </div>
        <p className="leading-relaxed">
          {result?.disclaimer ||
            "Tax calculations are estimates for analytical purposes and are not tax, legal, or financial advice. Actual liability depends on the taxpayer's complete circumstances, applicable deductions, credits, residency, filing status, state/local taxes, and other rules."}
        </p>
        <p className="text-[11px] text-text-tertiary/80">
          US: Federal estimate only. State and local taxes are not included unless explicitly selected. | Europe: Tax rules are country-specific; EU-level tax is not used as a single tax regime.
        </p>
      </div>
    </div>
  );
};
