from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "transaction-evidence-omission-v1"


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_count: int = Field(10, ge=0)
    max_fraction: float = Field(0.5, ge=0, le=1)
    max_amount_fraction: float | None = Field(None, ge=0, le=1)
    min_retained: int = Field(1, ge=0)
    max_interventions: int = Field(12, ge=0)


class InterventionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dataset_id: str = Field(min_length=1)
    source_identity: str = Field(min_length=1)
    time_kind: Literal["timestamp_utc", "simulation_hour"]
    cutoff: str
    window_size: int = Field(24, gt=0)
    window_unit: Literal["seconds", "hours"]
    simulation_timestamp_origin: str | None = None
    intervention_seed: int = Field(17, ge=0, le=4294967295)
    families: tuple[Literal["counterparty", "temporal", "budgeted"], ...] = ("counterparty", "temporal", "budgeted")
    budget: Budget = Budget()
    # Explicit universe must be known at cutoff, never inferred from future rows.
    known_accounts: tuple[str, ...] = ()
    max_reference_nodes: int = Field(10000, ge=1)

    @model_validator(mode="after")
    def validate_units(self):
        if self.time_kind == "simulation_hour" and self.window_unit != "hours":
            raise ValueError("Simulation steps use integral hours, not calendar dates.")
        if self.time_kind != "simulation_hour" and self.simulation_timestamp_origin is not None:
            raise ValueError("Simulation origin only applies to simulation-hour data.")
        if len(set(self.families)) != len(self.families):
            raise ValueError("Duplicate intervention families.")
        if any(not x.strip() for x in self.known_accounts):
            raise ValueError("Empty known account.")
        return self
