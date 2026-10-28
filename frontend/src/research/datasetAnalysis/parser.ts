/**
 * Fast RFC 4180-compliant client-side CSV / TSV / JSON parser
 * Works entirely in-memory with zero server upload.
 */
import type { ColumnMapping, TransactionRecord } from "./types";

export interface ParsedTable {
  headers: string[];
  rows: string[][];
  rawTotalRows: number;
}

export function parseDelimitedText(text: string, maxRows = 25000): ParsedTable {
  const clean = text.replace(/^\uFEFF/, "").trim();
  if (!clean) {
    throw new Error("File is empty.");
  }

  // Detect delimiter: check first line
  const firstLine = clean.split(/\r?\n/)[0] || "";
  let delimiter = ",";
  const commas = (firstLine.match(/,/g) || []).length;
  const tabs = (firstLine.match(/\t/g) || []).length;
  const semicolons = (firstLine.match(/;/g) || []).length;

  if (tabs > commas && tabs > semicolons) {
    delimiter = "\t";
  } else if (semicolons > commas && semicolons > tabs) {
    delimiter = ";";
  }

  // RFC-4180 state machine
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentField = "";
  let inQuotes = false;

  for (let i = 0; i < clean.length; i++) {
    const char = clean[i];
    const nextChar = clean[i + 1];

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          currentField += '"';
          i++; // skip escaped quote
        } else {
          inQuotes = false;
        }
      } else {
        currentField += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === delimiter) {
        currentRow.push(currentField.trim());
        currentField = "";
      } else if (char === "\r") {
        // ignore carriage return
      } else if (char === "\n") {
        currentRow.push(currentField.trim());
        if (currentRow.some((c) => c.length > 0)) {
          rows.push(currentRow);
          if (rows.length > maxRows + 1) throw new Error(`Dataset exceeds the ${maxRows.toLocaleString()} record limit. No partial analysis was performed.`);
        }
        currentRow = [];
        currentField = "";
      } else {
        currentField += char;
      }
    }
  }

  if (inQuotes) throw new Error("Unclosed quoted field in CSV.");

  // Flush remaining
  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField.trim());
    if (currentRow.some((c) => c.length > 0)) {
      rows.push(currentRow);
    }
  }

  if (rows.length < 2) {
    throw new Error("Dataset must contain at least a header and 1 row of transaction data.");
  }

  const headers = rows[0].map((h, idx) => h || `Col_${idx + 1}`);
  const dataRows = rows.slice(1);
  if (dataRows.length > maxRows) throw new Error(`Dataset exceeds the ${maxRows.toLocaleString()} record limit. No partial analysis was performed.`);

  return {
    headers,
    rows: dataRows,
    rawTotalRows: dataRows.length,
  };
}

export function parseJsonTransactions(jsonStr: string): ParsedTable {
  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonStr);
  } catch {
    throw new Error("Invalid JSON format. Expected an array of transaction objects.");
  }

  let items: unknown[] = [];
  if (Array.isArray(parsed)) {
    items = parsed;
  } else if (parsed && typeof parsed === "object") {
    const record = parsed as Record<string, unknown>;
    const arrayKey = Object.keys(record).find((k) => Array.isArray(record[k]));
    if (arrayKey) {
      items = record[arrayKey] as unknown[];
    }
  }

  if (!items.length || typeof items[0] !== "object") {
    throw new Error("JSON file does not contain a list of transaction records.");
  }

  if (items.length > 25000) throw new Error("Dataset exceeds the 25,000 record limit. No partial analysis was performed.");
  if (items.some(item => !item || typeof item !== "object" || Array.isArray(item))) throw new Error("Each JSON record must be an object.");
  const headers = [...new Set(items.flatMap(item => Object.keys(item as Record<string, unknown>)))];
  const rows = items.map((item) => {
    const obj = item as Record<string, unknown>;
    return headers.map((h) => String(obj[h] ?? ""));
  });

  return {
    headers,
    rows,
    rawTotalRows: items.length,
  };
}

export function autoDetectColumnMapping(headers: string[]): ColumnMapping {
  const norm = headers.map((h) => h.toLowerCase().replace(/[^a-z0-9]/g, ""));

  const findCol = (regex: RegExp): string => {
    const idx = norm.findIndex((h) => regex.test(h));
    return idx !== -1 ? headers[idx] : "";
  };

  // Source account detection
  const sourceCol =
    findCol(/^(source|sender|origin|from|nameorig|src|payer|fromaccount|sourceaccount)$/i) ||
    findCol(/source|sender|orig|from/i);

  // Destination account detection
  const destinationCol =
    findCol(/^(dest|destination|target|receiver|recipient|to|namedest|dst|payee|toaccount|destaccount)$/i) ||
    findCol(/dest|target|receiv|recip|namedest/i);

  // Amount detection
  const amountCol =
    findCol(/^(amount|amt|value|val|txval|total|transamount|txamount|volume)$/i) ||
    findCol(/amount|value|amt|val/i);

  // Optional columns
  const transactionIdCol =
    findCol(/^(transactionid|txid|transid|id|txhash|hash)$/i) ||
    findCol(/trans.*id|tx.*id/i);

  const timestampCol =
    findCol(/^(timestamp|step|time|date|datetime|txtime)$/i) ||
    findCol(/time|date|step/i);

  const typeCol =
    findCol(/^(type|action|category|txtype|transtype)$/i) ||
    findCol(/type|action/i);

  const currencyCol =
    findCol(/^(currency|curr|ccy|currencycode)$/i) ||
    findCol(/curr/i);

  const labelCol =
    findCol(/^(isfraud|fraud|isanomaly|anomaly|label|class|target|isflaggedfraud)$/i) ||
    findCol(/fraud|anom/i);

  const patternTypeCol =
    findCol(/^(patterntype|pattern|anomalytype|motif)$/i) ||
    findCol(/pattern/i);

  return {
    sourceCol,
    destinationCol,
    amountCol,
    transactionIdCol: transactionIdCol || (headers[0] !== sourceCol ? headers[0] : ""),
    timestampCol,
    typeCol,
    currencyCol,
    labelCol,
    patternTypeCol,
  };
}

export interface BuildRecordsResult {
  records: TransactionRecord[];
  acceptedRows: number;
  rejectedRows: number;
  rawTotalRows: number;
}

export function buildTransactionRecords(
  table: ParsedTable,
  mapping: ColumnMapping,
): TransactionRecord[] {
  const result = buildTransactionRecordsDetailed(table, mapping);
  return result.records;
}

export function buildTransactionRecordsDetailed(
  table: ParsedTable,
  mapping: ColumnMapping,
): BuildRecordsResult {
  const { headers, rows } = table;
  const colIdx = (name?: string) => (name ? headers.indexOf(name) : -1);

  const srcIdx = colIdx(mapping.sourceCol);
  const dstIdx = colIdx(mapping.destinationCol);
  const amtIdx = colIdx(mapping.amountCol);
  const idIdx = colIdx(mapping.transactionIdCol);
  const timeIdx = colIdx(mapping.timestampCol);
  const typeIdx = colIdx(mapping.typeCol);
  const currIdx = colIdx(mapping.currencyCol);
  const labelIdx = colIdx(mapping.labelCol);
  const patIdx = colIdx(mapping.patternTypeCol);

  if (srcIdx === -1 || dstIdx === -1 || amtIdx === -1) {
    throw new Error(
      "Source Account, Destination Account, and Amount must be mapped to valid columns.",
    );
  }

  const records: TransactionRecord[] = [];
  let rejectedRows = 0;

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const source = row[srcIdx]?.trim();
    const destination = row[dstIdx]?.trim();
    const rawAmt = row[amtIdx]?.replace(/[^0-9.-]/g, "");
    const amount = parseFloat(rawAmt || "0");

    if (!source || !destination || !Number.isFinite(amount) || amount <= 0) {
      rejectedRows++;
      continue; // skip invalid or non-positive records
    }

    let label: number | boolean | null = null;
    if (labelIdx !== -1 && row[labelIdx] !== undefined) {
      const val = row[labelIdx].toLowerCase().trim();
      if (val === "1" || val === "true" || val === "fraud" || val === "yes") {
        label = 1;
      } else if (val === "0" || val === "false" || val === "normal" || val === "no") {
        label = 0;
      }
    }

    const currency = currIdx !== -1 && row[currIdx] ? row[currIdx].trim().toUpperCase() : undefined;
    const pattern_type = patIdx !== -1 && row[patIdx] ? row[patIdx].trim() : undefined;

    records.push({
      transaction_id: idIdx !== -1 && row[idIdx] ? row[idIdx].trim() : `TX_${i + 1}`,
      source,
      destination,
      amount,
      timestamp: timeIdx !== -1 ? row[timeIdx]?.trim() : undefined,
      type: typeIdx !== -1 ? row[typeIdx]?.trim() : undefined,
      currency,
      label,
      pattern_type,
    });
  }

  if (records.length === 0) {
    throw new Error(
      "No valid transactions found. Ensure Source, Destination, and positive Amount exist.",
    );
  }

  return {
    records,
    acceptedRows: records.length,
    rejectedRows,
    rawTotalRows: rows.length,
  };
}
