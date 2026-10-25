from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "e6-crest-frozen-e4-v1"
MODES = ("E6_BASE", "E6_SENSITIVITY", "E6_ROBUSTNESS", "E6_HYBRID", "E6_CONCENTRATION_DIAGNOSTIC")
Mode = Literal["E6_BASE", "E6_SENSITIVITY", "E6_ROBUSTNESS", "E6_HYBRID", "E6_CONCENTRATION_DIAGNOSTIC"]


class CrestConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    source_dataset_id: str = Field(min_length=1)
    evaluation_dataset_id: str = Field(min_length=1)
    split_id: str = Field(min_length=1)
    source_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_ids: tuple[str, ...]
    evaluation_ids: tuple[str, ...]
    model_seed: int = Field(42, ge=0, le=4294967295)
    n_estimators: int = Field(100, ge=1)
    max_samples: int | float | Literal["auto"] = "auto"
    contamination: float = Field(.005, gt=0, le=.5)
    alpha: float = Field(.25, ge=0)
    beta: float = Field(.25, ge=0)
    modes: tuple[Mode, ...] = MODES
    min_robustness_per_family: int = Field(2, ge=2)
    min_concentration_per_stratum: int = Field(2, ge=2)
    fraction_edges: tuple[float, ...] = (0.0, .25, .5, .75, 1.0)
    amount_edges: tuple[float, ...] = (0.0, .25, .5, .75, 1.0)
    ranking_stratum: str | None = None
    batch_size: int = Field(1024, ge=1)

    @model_validator(mode="after")
    def check(self):
        if len(self.train_ids) < 2 or not self.evaluation_ids:
            raise ValueError("At least two source-training accounts and one evaluation account required.")
        for values in [self.train_ids, self.evaluation_ids, self.modes]:
            if len(set(values)) != len(values) or not values:
                raise ValueError("Empty or duplicate account/mode identifiers.")
        if any(not x.strip() for x in self.train_ids + self.evaluation_ids):
            raise ValueError("Empty account identifier.")
        if self.source_dataset_id == self.evaluation_dataset_id and set(self.train_ids) & set(self.evaluation_ids):
            raise ValueError("Held-out evaluation accounts overlap source training.")
        for edges in [self.fraction_edges, self.amount_edges]:
            if len(edges) < 2 or edges[0] != 0 or edges[-1] != 1 or any(a >= b for a,b in zip(edges,edges[1:])):
                raise ValueError("Stratum edges must strictly increase from 0 to 1.")
        return self
