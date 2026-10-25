"""Public read-only research contract, independent of production prediction APIs."""
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field

Status = Literal['verified','historical','exploratory','incomplete','unavailable']
ProvenanceStatus = Literal['verified','partially_verified','unresolved']
MetricName = Literal['average_precision','roc_auc','precision_at_10','precision_at_25','precision_at_50','precision_at_100']

class PublicModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Evidence(PublicModel):
    status: Status
    provenance_status: ProvenanceStatus
    artifact_id: str | None = None
    artifact_sha256: str | None = None
    limitations: list[str] = Field(default_factory=list)

T = TypeVar('T')
class Page(Evidence, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

class LabelSet(PublicModel):
    identity: str
    sha256: str
    accounts: int
    positives: int

class Dataset(Evidence):
    dataset_id: str
    name: str
    version: str
    dataset_type: Literal['synthetic'] = 'synthetic'
    tier: str
    accounts: int | None = None
    transactions: int | None = None
    positives: int | None = None
    negatives: int | None = None
    prevalence: float | None = None
    label_definition: str
    label_sets: list[LabelSet] = Field(default_factory=list)
    label_disagreements: int | None = None
    transaction_sha256: str | None = None
    time_semantics: str

class Retrieval(PublicModel):
    k: int
    effective_k: int
    positives: int
    precision: float | None
    recall: float | None

class Metrics(PublicModel):
    count: int | None = None
    positives: int | None = None
    prevalence: float | None = None
    average_precision: float | None = None
    roc_auc: float | None = None
    retrieval: list[Retrieval] = Field(default_factory=list)
    confidence_interval: tuple[float,float] | None = None
    uncertainty_note: str = 'No per-run AP confidence interval supplied by this endpoint.'

class Experiment(Evidence):
    experiment_id: str
    dataset_id: str
    tier: str
    method: str
    version: str
    feature_names: list[str] = Field(default_factory=list)
    split_seed: int | None = None
    model_seed: int | None = None
    population_identity: str | None = None
    dataset_sha256: str | None = None
    label_sha256: str | None = None
    train_sha256: str | None = None
    test_sha256: str | None = None
    metrics: Metrics | None = None

class Ranking(PublicModel):
    rank: int
    account_token: str
    anomaly_score: float | None

class Diagnostic(Evidence):
    diagnostic_id: str
    account_token: str
    method: str
    family: str | None = None
    available: bool
    valid: bool | None = None
    reason: str | None = None
    baseline_score: float | None
    intervened_score: float | None = None
    signed_fidelity: float | None = None
    omitted_count: int | None = None
    omitted_fraction: float | None = None
    omitted_amount_fraction: float | None = None

class ComparisonValue(PublicModel):
    experiment_id: str
    value: float | None

class Comparison(Evidence):
    metric: MetricName
    population_identity: str
    values: list[ComparisonValue]
    interpretation: str = 'Descriptive comparison only; no statistical significance or superiority implied.'

class Replay(PublicModel):
    tier: str
    byte_identical: bool
    evidence_sha256: str
    dataset_sha256: str
    feature_schema: str
    model_seed: int = 42

class Reproducibility(Evidence):
    replays: list[Replay]
    n_estimators: int
    max_samples: str
    contamination: float
    split_seeds: list[int]

class SeedRun(PublicModel):
    dataset_id: str
    tier: str
    method: str
    split_seed: int
    model_seed: int
    metrics: Metrics
    fit_score_seconds: float | None

class SeedSummary(PublicModel):
    tier: str
    method: str
    mean_ap: float | None
    sample_sd_ap: float | None
    minimum_ap: float | None
    maximum_ap: float | None

class Overlap(PublicModel):
    k: int
    overlap: float | None
    jaccard: float | None

class SeedPair(PublicModel):
    tier: str
    method: str
    first_model_seed: int
    second_model_seed: int
    spearman_ordinal: float | None
    top_k: list[Overlap]

class ModelSeeds(Evidence):
    runs: list[SeedRun]
    summaries: list[SeedSummary]
    pairs: list[SeedPair]

class Limitation(PublicModel):
    topic: str
    assessment: str
    description: str

class Limitations(Evidence):
    items: list[Limitation]

class Overview(Evidence):
    project_title: str
    datasets: list[Dataset]
    available_methods: list[str]
    completed_run_count: int
    completed_evaluation_count: int
    scales: list[str]
    model_seed_analysis_available: bool
    crest_diagnostics_available: bool
    reproducibility_available: bool
    unavailable_components: list[str]
