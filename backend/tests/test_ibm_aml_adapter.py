"""
Unit tests for IBM AML dataset converter (backend/scripts/convert_ibm_aml.py).

Tests:
1. Composite account key construction is correct and collision-resistant on hand-crafted cases.
2. Label aggregation rule matches the documented 'any involvement' logic on a hand-verifiable example.
3. Chunked reading produces identical output to reading the whole file at once.
4. --sample-accounts produces a self-consistent sub-network with no dangling transaction references.
"""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from backend.scripts.convert_ibm_aml import (
    build_composite_key,
    convert_ibm_aml,
    collect_sampled_accounts,
)


def test_composite_account_key_collision_resistance():
    """
    Test 1: Composite key construction correctly avoids cross-bank account collision.
    Identical account numbers at different banks MUST generate distinct composite keys.
    """
    # Different banks, same account string
    key_bank1 = build_composite_key("10", "ACC_9999")
    key_bank2 = build_composite_key("3208", "ACC_9999")
    assert key_bank1 == "10_ACC_9999"
    assert key_bank2 == "3208_ACC_9999"
    assert key_bank1 != key_bank2, "Collision: identical account strings across banks must not collide!"

    # Same bank, same account string
    key_bank1_repeat = build_composite_key("10", "ACC_9999")
    assert key_bank1 == key_bank1_repeat

    # Whitespace stripping
    key_padded = build_composite_key(" 10 ", " ACC_9999 ")
    assert key_padded == "10_ACC_9999"


def test_label_aggregation_any_involvement():
    """
    Test 2: Account-level label aggregation strictly implements the 'Any Involvement' rule.
    An account is flagged positive (1) if it appears as sender OR receiver in AT LEAST ONE
    laundering transaction (Is Laundering == 1), and 0 otherwise.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_csv = tmp_path / "raw_synthetic.csv"
        out_tx = tmp_path / "out_tx.csv"
        out_lbl = tmp_path / "out_labels.csv"

        # Construct hand-verifiable scenarios:
        # Bank 1: A -> B (Clean)
        # Bank 1: B -> C (Laundering = 1) -> B and C flagged 1!
        # Bank 2: D -> E (Clean)           -> D and E are 0 so far
        # Bank 2: F -> E (Laundering = 1) -> F and E flagged 1! (E was clean with D, but launder with F)
        # Bank 3: G -> H (Clean)           -> G and H remain 0
        data = [
            # Timestamp, From Bank, Account, To Bank, Account.1, Amount Received, Receiving Currency, Amount Paid, Payment Currency, Payment Format, Is Laundering
            ["2022/09/01 00:00", "1", "A", "1", "B", "100.0", "USD", "100.0", "USD", "Cheque", 0],
            ["2022/09/01 01:00", "1", "B", "1", "C", "500.0", "USD", "500.0", "USD", "Wire", 1],
            ["2022/09/01 02:00", "2", "D", "2", "E", "200.0", "USD", "200.0", "USD", "Credit Card", 0],
            ["2022/09/01 03:00", "2", "F", "2", "E", "999.0", "USD", "999.0", "USD", "Wire", 1],
            ["2022/09/01 04:00", "3", "G", "3", "H", "300.0", "USD", "300.0", "USD", "Cash", 0],
        ]
        columns = [
            "Timestamp", "From Bank", "Account", "To Bank", "Account.1",
            "Amount Received", "Receiving Currency", "Amount Paid",
            "Payment Currency", "Payment Format", "Is Laundering"
        ]
        pd.DataFrame(data, columns=columns).to_csv(raw_csv, index=False)

        summary = convert_ibm_aml(
            input_file=raw_csv,
            output_tx_file=out_tx,
            output_labels_file=out_lbl,
            chunksize=2,
        )

        labels_df = pd.read_csv(out_lbl)
        label_dict = dict(zip(labels_df["user_id"], labels_df["label"]))

        # Hand verification:
        assert label_dict["1_A"] == 0, "Account 1_A was only in a clean transaction -> label 0"
        assert label_dict["1_B"] == 1, "Account 1_B was sender in laundering tx -> label 1"
        assert label_dict["1_C"] == 1, "Account 1_C was receiver in laundering tx -> label 1"
        assert label_dict["2_D"] == 0, "Account 2_D was only in clean tx -> label 0"
        assert label_dict["2_E"] == 1, "Account 2_E had clean tx with D, but receiver in laundering with F -> label 1"
        assert label_dict["2_F"] == 1, "Account 2_F was sender in laundering tx -> label 1"
        assert label_dict["3_G"] == 0, "Account 3_G was only in clean tx -> label 0"
        assert label_dict["3_H"] == 0, "Account 3_H was only in clean tx -> label 0"

        assert summary["unique_accounts"] == 8
        assert summary["positive_labels"] == 4
        assert summary["negative_labels"] == 4
        assert summary["prevalence_rate"] == 50.0


def test_chunked_reading_produces_identical_output():
    """
    Test 3: Chunked reading produces identical output to reading the whole file at once.
    Ensures that streaming in small increments does not drop transactions, split IDs incorrectly,
    or miscalculate ground-truth labels.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_csv = tmp_path / "raw_series.csv"

        # Generate 15 distinct transactions across 6 accounts
        rows = []
        for i in range(15):
            sender_idx = i % 5
            receiver_idx = (i + 1) % 5
            launder = 1 if i in (3, 7, 11) else 0
            rows.append(
                [
                    f"2022/09/01 {i:02d}:00",
                    "10",
                    f"ACCT_{sender_idx}",
                    "20",
                    f"ACCT_{receiver_idx}",
                    f"{(i+1)*10.0}",
                    "USD",
                    f"{(i+1)*10.0}",
                    "USD",
                    "Wire",
                    launder,
                ]
            )

        columns = [
            "Timestamp", "From Bank", "Account", "To Bank", "Account.1",
            "Amount Received", "Receiving Currency", "Amount Paid",
            "Payment Currency", "Payment Format", "Is Laundering"
        ]
        pd.DataFrame(rows, columns=columns).to_csv(raw_csv, index=False)

        # Run 1: Chunksize 3 (forces 5 distinct chunk reads)
        out_tx_chunked = tmp_path / "tx_chunked.csv"
        out_lbl_chunked = tmp_path / "lbl_chunked.csv"
        convert_ibm_aml(
            input_file=raw_csv,
            output_tx_file=out_tx_chunked,
            output_labels_file=out_lbl_chunked,
            chunksize=3,
        )

        # Run 2: Chunksize 100 (reads entire file in one chunk)
        out_tx_whole = tmp_path / "tx_whole.csv"
        out_lbl_whole = tmp_path / "lbl_whole.csv"
        convert_ibm_aml(
            input_file=raw_csv,
            output_tx_file=out_tx_whole,
            output_labels_file=out_lbl_whole,
            chunksize=100,
        )

        df_tx_chunked = pd.read_csv(out_tx_chunked)
        df_tx_whole = pd.read_csv(out_tx_whole)
        pd.testing.assert_frame_equal(df_tx_chunked, df_tx_whole)

        df_lbl_chunked = pd.read_csv(out_lbl_chunked)
        df_lbl_whole = pd.read_csv(out_lbl_whole)
        pd.testing.assert_frame_equal(df_lbl_chunked, df_lbl_whole)


def test_sample_accounts_produces_self_consistent_subnetwork():
    """
    Test 4: --sample-accounts produces a self-consistent sub-network with NO dangling references.
    Every sender_id and receiver_id in the output transactions must belong strictly to the sampled
    accounts set, and labels match exactly the accounts present in the output network.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_csv = tmp_path / "raw_network.csv"
        out_tx = tmp_path / "sub_tx.csv"
        out_lbl = tmp_path / "sub_lbl.csv"

        # Create 10 accounts: ACC_0 through ACC_9 with interconnected transactions
        rows = []
        for i in range(30):
            s = f"ACC_{i % 10}"
            r = f"ACC_{(i * 3 + 1) % 10}"
            if s == r:
                r = f"ACC_{(i * 3 + 2) % 10}"
            launder = 1 if i % 6 == 0 else 0
            rows.append(
                [
                    f"2022/09/01 {i % 24:02d}:00",
                    "1",
                    s,
                    "1",
                    r,
                    "50.0",
                    "USD",
                    "50.0",
                    "USD",
                    "Cheque",
                    launder,
                ]
            )

        columns = [
            "Timestamp", "From Bank", "Account", "To Bank", "Account.1",
            "Amount Received", "Receiving Currency", "Amount Paid",
            "Payment Currency", "Payment Format", "Is Laundering"
        ]
        pd.DataFrame(rows, columns=columns).to_csv(raw_csv, index=False)

        # Sample 4 accounts
        target_n = 4
        summary = convert_ibm_aml(
            input_file=raw_csv,
            output_tx_file=out_tx,
            output_labels_file=out_lbl,
            chunksize=5,
            sample_accounts=target_n,
            seed=42,
        )

        tx_df = pd.read_csv(out_tx)
        lbl_df = pd.read_csv(out_lbl)

        assert len(tx_df) > 0, "Sampled sub-network must contain transactions."
        active_senders = set(tx_df["sender_id"])
        active_receivers = set(tx_df["receiver_id"])
        active_accounts = active_senders.union(active_receivers)

        label_accounts = set(lbl_df["user_id"])

        # Check self-consistency: labels must match active accounts
        assert label_accounts == active_accounts, (
            "Labels must exactly cover all active accounts in the output transaction sub-network."
        )

        # Check no dangling references
        assert active_senders.issubset(label_accounts)
        assert active_receivers.issubset(label_accounts)

        # Canonical columns must exist
        for col in ["transaction_id", "sender_id", "receiver_id", "amount", "timestamp", "transaction_type"]:
            assert col in tx_df.columns
