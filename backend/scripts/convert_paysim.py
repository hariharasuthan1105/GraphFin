"""
PaySim Dataset Converter for GraphFin.

Standalone script to convert raw transactions from the Kaggle PaySim dataset
(PS_20174392719_1491204439457_log.csv) into GraphFin's canonical schema
and generate account-level ground-truth labels.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random
import sys
from typing import Dict, List, Optional, Set

import pandas as pd


RAW_REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "nameDest",
    "isFraud",
]


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PaySim synthetic transaction dataset into GraphFin canonical format."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="data/raw/PS_20174392719_1491204439457_log.csv",
        help="Path to the raw PaySim CSV file.",
    )
    parser.add_argument(
        "--output-tx",
        "-o",
        type=str,
        default="data/research/paysim_transactions.csv",
        help="Path to output canonical transactions CSV.",
    )
    parser.add_argument(
        "--output-labels",
        "-l",
        type=str,
        default="data/research/paysim_labels.csv",
        help="Path to output account-level ground-truth labels CSV.",
    )
    parser.add_argument(
        "--chunksize",
        "-c",
        type=int,
        default=100000,
        help="Number of rows per chunk for memory-safe reading (default: 100000).",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=None,
        help="Process only the first N rows of the raw file.",
    )
    parser.add_argument(
        "--sample-accounts",
        type=int,
        default=None,
        help="Sample N accounts and output only transactions between sampled accounts.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible account sampling (default: 42).",
    )
    return parser.parse_args(args)


def convert_paysim(
    input_file: str | Path,
    output_tx_file: str | Path,
    output_labels_file: str | Path,
    chunksize: int = 100000,
    sample_rows: Optional[int] = None,
    sample_accounts: Optional[int] = None,
    seed: int = 42,
) -> Dict[str, object]:
    """
    Convert PaySim dataset in chunks, writing canonical transactions and labels.
    Returns conversion summary statistics.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    out_tx_path = Path(output_tx_file).resolve()
    out_labels_path = Path(output_labels_file).resolve()
    out_tx_path.parent.mkdir(parents=True, exist_ok=True)
    out_labels_path.parent.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2023, 1, 1, 0, 0, 0)

    total_rows_in = 0
    total_rows_out = 0
    valid_rows_count = 0
    invalid_rows_count = 0

    account_labels: Dict[str, int] = {}
    first_chunk = True
    tx_counter = 1

    if out_tx_path.exists():
        out_tx_path.unlink()

    # Read raw CSV (full or sampled across full row index range)
    if sample_rows is not None:
        full_raw_df = pd.read_csv(input_path, dtype=str)
        if len(full_raw_df) > sample_rows:
            sampled_raw_df = full_raw_df.sample(n=sample_rows, random_state=seed).sort_index().reset_index(drop=True)
        else:
            sampled_raw_df = full_raw_df
        chunks = [sampled_raw_df]
    else:
        chunks = pd.read_csv(input_path, chunksize=chunksize, dtype=str)

    # Streaming chunks
    for chunk in chunks:
        total_rows_in += len(chunk)

        missing = [c for c in RAW_REQUIRED_COLUMNS if c not in chunk.columns]
        if missing:
            raise ValueError(f"Input CSV missing required columns: {missing}")

        senders = chunk["nameOrig"].astype(str).str.strip()
        receivers = chunk["nameDest"].astype(str).str.strip()

        amounts = pd.to_numeric(chunk["amount"], errors="coerce")
        fraud_flags = pd.to_numeric(chunk["isFraud"], errors="coerce").fillna(0).astype(int)
        steps = pd.to_numeric(chunk["step"], errors="coerce").fillna(1).astype(int)
        tx_types = chunk["type"].astype(str).str.strip()

        is_self_transfer = senders == receivers
        is_amount_valid = amounts.notna() & (amounts > 0)
        is_sender_valid = senders.str.len() > 1
        is_receiver_valid = receivers.str.len() > 1

        valid_mask = (
            (~is_self_transfer)
            & is_amount_valid
            & is_sender_valid
            & is_receiver_valid
        )

        invalid_rows_count += int((~valid_mask).sum())
        valid_rows_count += int(valid_mask.sum())

        if not valid_mask.any():
            continue

        active_senders = senders[valid_mask].tolist()
        active_receivers = receivers[valid_mask].tolist()
        active_amounts = amounts[valid_mask].tolist()
        active_steps = steps[valid_mask].tolist()
        active_types = tx_types[valid_mask].tolist()
        active_fraud = fraud_flags[valid_mask].tolist()

        n_active = len(active_senders)
        tx_ids = [f"TX_PS_{i:08d}" for i in range(tx_counter, tx_counter + n_active)]
        tx_counter += n_active

        timestamps = [
            (base_time + timedelta(hours=s)).strftime("%Y-%m-%d %H:%M:%S")
            for s in active_steps
        ]

        # Update account labels using "Any Involvement" rule
        for s, r, is_f in zip(active_senders, active_receivers, active_fraud):
            is_pos = 1 if is_f == 1 else 0
            account_labels[s] = account_labels.get(s, 0) | is_pos
            account_labels[r] = account_labels.get(r, 0) | is_pos

        out_df = pd.DataFrame(
            {
                "transaction_id": tx_ids,
                "sender_id": active_senders,
                "receiver_id": active_receivers,
                "amount": [round(a, 2) for a in active_amounts],
                "timestamp": timestamps,
                "transaction_type": active_types,
            }
        )

        out_df.to_csv(out_tx_path, mode="a", header=first_chunk, index=False)
        first_chunk = False
        total_rows_out += len(out_df)

    # If sampling target account count:
    if sample_accounts is not None and sample_accounts > 0 and len(account_labels) > sample_accounts:
        rng = random.Random(seed)
        all_accts = sorted(list(account_labels.keys()))
        # Ensure fraud accounts are included in sample if possible
        pos_accts = [a for a in all_accts if account_labels[a] == 1]
        neg_accts = [a for a in all_accts if account_labels[a] == 0]
        rng.shuffle(pos_accts)
        rng.shuffle(neg_accts)

        num_pos = min(len(pos_accts), int(sample_accounts * 0.05) or 10)
        num_neg = sample_accounts - num_pos

        target_set = set(pos_accts[:num_pos] + neg_accts[:num_neg])

        # Filter output files to target_set
        full_tx_df = pd.read_csv(out_tx_path)
        filtered_tx_df = full_tx_df[
            full_tx_df["sender_id"].astype(str).isin(target_set)
            & full_tx_df["receiver_id"].astype(str).isin(target_set)
        ].copy()
        filtered_tx_df.to_csv(out_tx_path, index=False)
        total_rows_out = len(filtered_tx_df)

        account_labels = {k: v for k, v in account_labels.items() if k in target_set}

    # Output ground-truth labels CSV
    label_records = [{"user_id": uid, "label": lbl} for uid, lbl in sorted(account_labels.items())]
    labels_df = pd.DataFrame(label_records, columns=["user_id", "label"])
    labels_df.to_csv(out_labels_path, index=False)

    unique_accounts = len(account_labels)
    positive_labels = sum(account_labels.values())
    negative_labels = unique_accounts - positive_labels
    prevalence_rate = (positive_labels / unique_accounts * 100.0) if unique_accounts > 0 else 0.0

    summary = {
        "rows_in": total_rows_in,
        "rows_out": total_rows_out,
        "valid_rows": valid_rows_count,
        "invalid_rows": invalid_rows_count,
        "unique_accounts": unique_accounts,
        "positive_labels": positive_labels,
        "negative_labels": negative_labels,
        "prevalence_rate": round(prevalence_rate, 4),
        "output_tx_path": str(out_tx_path),
        "output_labels_path": str(out_labels_path),
    }

    print("=" * 70)
    print("PAYSIM DATASET CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Total Rows Processed (In)    : {total_rows_in:,}")
    print(f"Valid Rows Identified        : {valid_rows_count:,}")
    print(f"Invalid Rows Excluded        : {invalid_rows_count:,} (self-transfers / non-positive amounts)")
    print(f"Transactions Written (Out)   : {total_rows_out:,}")
    print(f"Unique Accounts Extracted    : {unique_accounts:,}")
    print(f"Negative Accounts (label=0)  : {negative_labels:,}")
    print(f"Positive Accounts (label=1)  : {positive_labels:,}")
    print(f"Account Prevalence Rate      : {prevalence_rate:.4f}%")
    print("=" * 70)
    print(f"Transactions saved to : {out_tx_path}")
    print(f"Labels saved to       : {out_labels_path}")
    print("=" * 70)

    return summary


def main():
    args = parse_args()
    convert_paysim(
        input_file=args.input,
        output_tx_file=args.output_tx,
        output_labels_file=args.output_labels,
        chunksize=args.chunksize,
        sample_rows=args.sample_rows,
        sample_accounts=args.sample_accounts,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
