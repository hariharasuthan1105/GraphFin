"""Immutable event table. No label columns are read or accepted as selectors."""
from dataclasses import dataclass
from decimal import Decimal
import io
import math
import pandas as pd
from ...services.research_protocol import canonical, sha


def event_time(value, kind):
    if kind == "simulation_hour":
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number != number.to_integral_value():
            raise ValueError("Simulation step must be a nonnegative integral hour.")
        return int(number)
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError("Missing timestamp.")
    parsed = parsed.tz_localize("UTC") if parsed.tzinfo is None else parsed.tz_convert("UTC")
    return parsed.value  # nanoseconds UTC; naive input explicitly interpreted as UTC


@dataclass(frozen=True)
class Event:
    transaction_id: str
    sender: str
    receiver: str
    amount: str
    time: int
    source_row: int


@dataclass(frozen=True)
class History:
    events: tuple[Event, ...]
    dataset_sha256: str
    history_sha256: str
    universe: tuple[str, ...]
    cutoff: int
    time_kind: str

    def frame(self, omitted=()):
        omitted = tuple(omitted)
        if len(set(omitted)) != len(omitted) or not set(omitted) <= {e.transaction_id for e in self.events}:
            raise ValueError("Omission must name unique eligible transaction IDs.")
        omitted = frozenset(omitted)
        rows = []
        for e in self.events:
            if e.transaction_id in omitted:
                continue
            # Arithmetic bridge only: synthetic epoch is NOT an observed event date.
            ts = (pd.Timestamp("1970-01-01", tz="UTC") + pd.Timedelta(hours=e.time)
                  if self.time_kind == "simulation_hour" else pd.Timestamp(e.time, tz="UTC"))
            rows.append((e.transaction_id, e.sender, e.receiver, float(e.amount), ts))
        return pd.DataFrame(rows, columns=["transaction_id", "sender_id", "receiver_id", "amount", "timestamp"])


def load_history(content: bytes, config):
    table = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    time_col = "step" if config.time_kind == "simulation_hour" else "timestamp"
    if time_col == "step" and "step" not in table and config.simulation_timestamp_origin is not None:
        if "timestamp" not in table:
            raise ValueError("Missing simulation timestamp.")
        origin = event_time(config.simulation_timestamp_origin, "timestamp_utc")
        table["step"] = [str(Decimal(event_time(t, "timestamp_utc")-origin) / Decimal(3600*10**9))
                         for t in table.timestamp]
    required = ["sender_id", "receiver_id", "amount", time_col]
    if not set(required).issubset(table.columns):
        raise ValueError(f"Missing canonical columns: {required}; simulation requires explicit step.")
    cutoff = event_time(config.cutoff, config.time_kind)
    events, seen = [], set()
    # Source row order is immutable identity, independent of labels and future values.
    for row_number, row in enumerate(table.to_dict("records"), start=1):
        time = event_time(row[time_col], config.time_kind)
        if time > cutoff:
            continue  # no future endpoints, amounts, IDs or labels enter history
        sender, receiver = row["sender_id"], row["receiver_id"]
        if not sender.strip() or not receiver.strip() or sender != sender.strip() or receiver != receiver.strip():
            raise ValueError("Blank or whitespace-padded account ID.")
        if sender == receiver:
            raise ValueError("Self-transfer unsupported, consistent with canonical nonself input policy.")
        amount = Decimal(row["amount"])
        if not amount.is_finite() or amount <= 0 or not math.isfinite(float(amount)):
            raise ValueError("Amount must be finite and positive.")
        txid = row.get("transaction_id")
        if not txid:
            if not row.get("source_row_id"):
                raise ValueError("Missing native ID requires an explicit immutable source_row_id.")
            txid = sha(canonical([config.source_identity, row["source_row_id"]]))
        if txid in seen:
            raise ValueError("Duplicate native transaction ID; distinct events require distinct IDs.")
        seen.add(txid)
        events.append(Event(txid, sender, receiver, str(amount), time, row_number))
    universe = tuple(sorted(set(config.known_accounts) | {x for e in events for x in (e.sender, e.receiver)}))
    # Physical line offsets are diagnostic only: inserting future rows must not
    # alter historical identity, ordering or generated interventions.
    payload = [[e.transaction_id, e.sender, e.receiver, e.amount, e.time] for e in events]
    return History(tuple(events), sha(content), sha(canonical(payload)), universe, cutoff, config.time_kind)
