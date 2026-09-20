import { NetworkEdge } from "../types/api";

export interface ParsedTransaction {
  transaction_id: string;
  sender_id: string;
  receiver_id: string;
  amount: number;
  timestamp: string;
  transaction_type?: string;
  merchant?: string;
  location?: string;
  device?: string;
}

export function parseTransactionCsv(csvText: string): {
  transactions: ParsedTransaction[];
  edges: NetworkEdge[];
  nodes: Set<string>;
} {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) {
    return { transactions: [], edges: [], nodes: new Set() };
  }

  const header = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const txIdIdx = header.indexOf("transaction_id");
  const senderIdx = header.indexOf("sender_id");
  const receiverIdx = header.indexOf("receiver_id");
  const amountIdx = header.indexOf("amount");
  const timeIdx = header.indexOf("timestamp");

  const transactions: ParsedTransaction[] = [];
  const edgeMap = new Map<string, NetworkEdge>();
  const nodes = new Set<string>();

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",").map((c) => c.trim());
    if (cols.length <= Math.max(txIdIdx, senderIdx, receiverIdx, amountIdx)) continue;

    const sender = cols[senderIdx] || "";
    const receiver = cols[receiverIdx] || "";
    const amount = parseFloat(cols[amountIdx]) || 0;
    const txId = cols[txIdIdx] || `TX_${i}`;
    const timestamp = cols[timeIdx] || "";

    if (!sender || !receiver) continue;

    nodes.add(sender);
    nodes.add(receiver);

    transactions.push({
      transaction_id: txId,
      sender_id: sender,
      receiver_id: receiver,
      amount,
      timestamp,
    });

    const edgeKey = `${sender}->${receiver}`;
    const existing = edgeMap.get(edgeKey);
    if (existing) {
      existing.amount += amount;
      existing.count += 1;
    } else {
      edgeMap.set(edgeKey, {
        source: sender,
        target: receiver,
        amount,
        count: 1,
      });
    }
  }

  return {
    transactions,
    edges: Array.from(edgeMap.values()),
    nodes,
  };
}
