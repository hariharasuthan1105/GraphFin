export interface TaxBracketBreakdown {
  bracket_label: string;
  min_income: number;
  max_income: number | null;
  taxable_amount_in_bracket: number;
  rate: number;
  tax_amount: number;
}

export interface TaxCalculationRequest {
  jurisdiction: string;
  tax_year: string;
  taxable_income?: number;
  gross_income?: number;
  currency?: string;
  filing_status?: string;
  region?: string;
  age?: number;
  residency_status?: string;
  deductions?: number;
  church_tax?: boolean;
  church_tax_rate?: number;
  parts?: number;
}

export interface TaxCalculationResponse {
  jurisdiction: string;
  country: string;
  tax_year: string;
  currency: string;
  currency_symbol: string;
  taxable_income: number;
  gross_income?: number;
  allowances_and_deductions: number;
  tax_before_reliefs: number;
  reliefs: number;
  tax_after_reliefs: number;
  surcharge: number;
  cess_or_additional_tax: number;
  church_tax: number;
  estimated_tax: number;
  effective_tax_rate: number;
  marginal_tax_rate: number;
  breakdown: TaxBracketBreakdown[];
  extra_details: Record<string, any>;
  rule_version: string;
  source: string;
  source_url: string;
  last_verified: string;
  disclaimer: string;
}

export interface JurisdictionInfo {
  id: string;
  name: string;
  supported_years: string[];
  currency: string;
  currency_symbol: string;
  source: string;
  source_url: string;
  filing_statuses?: string[];
  regions?: string[];
}

export interface TaxRuleMetadata {
  jurisdiction: string;
  country: string;
  tax_year: string;
  rule_version: string;
  currency: string;
  currency_symbol: string;
  source: string;
  source_url: string;
  last_verified: string;
  disclaimer: string;
  brackets: Array<{
    label: string;
    min: number;
    max: number | null;
    rate_percent: number;
  }>;
  options?: Record<string, any>;
}
