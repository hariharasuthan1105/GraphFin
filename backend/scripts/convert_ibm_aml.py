"""
IBM AML Synthetic Dataset Converter for GraphFin.

Standalone script to convert raw transactions from the Kaggle
"IBM Transactions for Anti-Money Laundering" dataset (HI-Small variant)
into GraphFin's canonical schema and generate account-level ground-truth labels.

=============================================================================
DOCUMENTED METHODOLOGICAL AND MODELING CHOICES
=============================================================================
1. COMPOSITE ACCOUNT IDENTIFIER:
   Raw account numbers ('Account', 'Account.1') in the IBM AML dataset are local
   identifiers within each institution ('From Bank', 'To Bank'). Because distinct
   banks may assign identical account strings to different entities, constructing
   the graph directly on raw account strings would induce false inter-bank entity
   collisions. We construct a globally unique, collision-resistant composite key:
       sender_id   = str(From Bank) + "_" + str(Account)
       receiver_id = str(To Bank)   + "_" + str(Account.1)

2. CANONICAL AMOUNT CHOICE (Amount Paid):
   The dataset contains both 'Amount Received' and 'Amount Paid' along with foreign
   exchange currencies. We select 'Amount Paid' as the canonical amount because
   it represents the sender's committed monetary value in the originating currency
   from the payer's perspective, avoiding unstated assumptions or artifacts from
   approximate exchange rate conversions.

3. ACCOUNT-LEVEL GROUND-TRUTH LABEL AGGREGATION ("ANY INVOLVEMENT" RULE):
   The raw dataset provides transaction-level flags ('Is Laundering' in {0, 1}).
   GraphFin evaluates entity-level (account-level) anomaly detection.
   We aggregate transaction flags to account labels using the "Any Involvement" rule:
       - An account is assigned label = 1 if it participates as either sender OR
         receiver in AT LEAST ONE transaction where Is Laundering == 1.
       - An account is assigned label = 0 if it NEVER participates in any laundering
         transaction across its observed history.
   Methodological rationale: In financial crime forensics and SAR reporting, any
   direct flow through an account (source, transit/layering node, or beneficiary)
   flags that account as an active participant in the illicit scheme.

4. TRANSACTION VALIDATION AND SELF-TRANSFER FILTERING:
   GraphFin's transaction schema rejects self-transfers (sender_id == receiver_id)
   as invalid cycles that do not represent inter-account edge flows. Rows with
   identical sender and receiver composite IDs or non-positive amounts are tracked
   as invalid rows, excluded from the output transactions, and counted in the
   audit summary.

5. DETERMINISTIC SYNTHETIC TRANSACTION ID:
   Since the raw dataset lacks a transaction identifier, we generate deterministic
   sequential IDs ('TX_IBM_{idx:08d}') to ensure reproducible, idempotently
   traceable records.
=============================================================================
"""

import argparse
import os
from pathlib import Path
import random
import sys
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd


RAW_REQUIRED_COLUMNS = [
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account.1",
    "Amount Paid",
    "Payment Format",
    "Is Laundering",
]


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert IBM AML synthetic transaction dataset into GraphFin canonical format."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to the raw IBM AML CSV file (e.g. HI-Small_Trans.csv).",
    )
    parser.add_argument(
        "--output-tx",
        "-o",
        type=str,
        required=True,
        help="Path to output canonical transactions CSV.",
    )
    parser.add_argument(
        "--output-labels",
        "-l",
        type=str,
        required=True,
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


def build_composite_key(bank: object, account: object) -> str:
    """Build a composite account identifier: <Bank>_<Account>."""
    return f"{str(bank).strip()}_{str(account).strip()}"


def collect_sampled_accounts(
    input_path: Path,
    target_accounts: int,
    chunksize: int,
    sample_rows: Optional[int] = None,
    seed: int = 42,
) -> Set[str]:
    """
    Select target_accounts by streaming transactions to build a self-consistent,
    connected candidate network.
    """
    rng = random.Random(seed)
    sampled_set: Set[str] = set()
    total_read = 0

    # Stream through chunks to collect accounts participating in valid transactions
    for chunk in pd.read_csv(input_path, chunksize=chunksize, dtype=str):
        if sample_rows is not None and total_read >= sample_rows:
            break

        if sample_rows is not None and total_read + len(chunk) > sample_rows:
            chunk = chunk.iloc[: sample_rows - total_read]

        total_read += len(chunk)

        from_bank = chunk["From Bank"].astype(str).str.strip()
        from_acct = chunk["Account"].astype(str).str.strip()
        to_bank = chunk["To Bank"].astype(str).str.strip()
        to_acct = chunk["Account.1"].astype(str).str.strip()

        senders = from_bank + "_" + from_acct
        receivers = to_bank + "_" + to_acct

        # Discard self-transfers when collecting accounts
        valid_mask = senders != receivers

        for s, r in zip(senders[valid_mask], receivers[valid_mask]):
            sampled_set.add(s)
            sampled_set.add(r)
            if len(sampled_set) >= target_accounts:
                break

        if len(sampled_set) >= target_accounts:
            break

    # If we collected more than target_accounts, trim down deterministically with seed
    if len(sampled_set) > target_accounts:
        sorted_accts = sorted(list(sampled_set))
        rng.shuffle(sorted_accts)
        sampled_set = set(sorted_accts[:target_accounts])

    return sampled_set


def convert_ibm_aml(
    input_file: str | Path,
    output_tx_file: str | Path,
    output_labels_file: str | Path,
    chunksize: int = 100000,
    sample_rows: Optional[int] = None,
    sample_accounts: Optional[int] = None,
    seed: int = 42,
) -> Dict[str, object]:
    """
    Convert IBM AML dataset in chunks, writing canonical transactions and labels.
    Returns conversion summary statistics.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    out_tx_path = Path(output_tx_file).resolve()
    out_labels_path = Path(output_labels_file).resolve()
    out_tx_path.parent.mkdir(parents=True, exist_ok=True)
    out_labels_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. If sampling by accounts, pre-select the account subset
    target_account_set: Optional[Set[str]] = None
    if sample_accounts is not None and sample_accounts > 0:
        target_account_set = collect_sampled_accounts(
            input_path=input_path,
            target_accounts=sample_accounts,
            chunksize=chunksize,
            sample_rows=sample_rows,
            seed=seed,
        )

    # 2. Process transactions in chunks
    total_rows_in = 0
    total_rows_out = 0
    valid_rows_count = 0
    invalid_rows_count = 0

    # Account tracking for labels: account_id -> bool (has laundering transaction)
    account_labels: Dict[str, int] = {}

    first_chunk = True
    tx_counter = 1

    # Remove existing output files if present
    if out_tx_path.exists():
        out_tx_path.unlink()

    for chunk in pd.read_csv(input_path, chunksize=chunksize, dtype=str):
        if sample_rows is not None and total_rows_in >= sample_rows:
            break

        if sample_rows is not None and total_rows_in + len(chunk) > sample_rows:
            chunk = chunk.iloc[: sample_rows - total_rows_in]

        total_rows_in += len(chunk)

        # Ensure required raw columns exist
        missing = [c for c in RAW_REQUIRED_COLUMNS if c not in chunk.columns]
        if missing:
            raise ValueError(f"Input CSV missing required columns: {missing}")

        # Build composite identifiers
        senders = chunk["From Bank"].astype(str).str.strip() + "_" + chunk["Account"].astype(str).str.strip()
        receivers = chunk["To Bank"].astype(str).str.strip() + "_" + chunk["Account.1"].astype(str).str.strip()

        # Parse amounts
        amounts = pd.to_numeric(chunk["Amount Paid"], errors="coerce")

        # Parse laundering flags
        laundering_flags = pd.to_numeric(chunk["Is Laundering"], errors="coerce").fillna(0).astype(int)

        # Timestamps
        timestamps = chunk["Timestamp"].astype(str).str.strip()

        # Payment format (optional transaction_type passthrough)
        payment_formats = chunk["Payment Format"].astype(str).str.strip()

        # Identify valid vs invalid rows
        # Valid: amount > 0, sender != receiver, non-empty identifiers and timestamps
        is_self_transfer = senders == receivers
        is_amount_valid = amounts.notna() & (amounts > 0)
        is_sender_valid = senders.str.len() > 1
        is_receiver_valid = receivers.str.len() > 1
        is_timestamp_valid = timestamps.str.len() > 0

        valid_mask = (
            (~is_self_transfer)
            & is_amount_valid
            & is_sender_valid
            & is_receiver_valid
            & is_timestamp_valid
        )

        invalid_rows_count += int((~valid_mask).sum())
        valid_rows_count += int(valid_mask.sum())

        # If filtering by target accounts, keep only transactions between sampled accounts
        if target_account_set is not None:
            account_filter_mask = senders.isin(target_account_set) & receivers.isin(target_account_set)
            active_mask = valid_mask & account_filter_mask
        else:
            active_mask = valid_mask

        if not active_mask.any():
            continue

        active_senders = senders[active_mask].tolist()
        active_receivers = receivers[active_mask].tolist()
        active_amounts = amounts[active_mask].tolist()
        active_timestamps = timestamps[active_mask].tolist()
        active_formats = payment_formats[active_mask].tolist()
        active_laundering = laundering_flags[active_mask].tolist()

        n_active = len(active_senders)
        tx_ids = [f"TX_IBM_{i:08d}" for i in range(tx_counter, tx_counter + n_active)]
        tx_counter += n_active

        # Update account labels using "Any Involvement" rule
        for s, r, is_laundering in zip(active_senders, active_receivers, active_laundering):
            is_pos = 1 if is_laundering == 1 else 0
            account_labels[s] = account_labels.get(s, 0) | is_pos
            account_labels[r] = account_labels.get(r, 0) | is_pos

        # Prepare canonical transaction DataFrame
        out_df = pd.DataFrame(
            {
                "transaction_id": tx_ids,
                "sender_id": active_senders,
                "receiver_id": active_receivers,
                "amount": [round(a, 2) for a in active_amounts],
                "timestamp": active_timestamps,
                "transaction_type": active_formats,
            }
        )

        out_df.to_csv(out_tx_path, mode="a", header=first_chunk, index=False)
        first_chunk = False
        total_rows_out += len(out_df)

    # 3. Output account-level ground-truth labels CSV
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
    print("IBM AML DATASET CONVERSION SUMMARY")
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
    convert_ibm_aml(
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
