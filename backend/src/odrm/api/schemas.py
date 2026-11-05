from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from odrm.domain.tea_defaults import (
    DEFAULT_CO2_UTILIZATION_FRACTION,
    DEFAULT_OPERATING_DAYS_PER_YEAR,
    DEFAULT_OPERATING_HOURS_PER_DAY,
    DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR,
)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Reject unexpected fields

    temperature_c: float = Field(ge=500, le=1000)
    pressure_bar: float = Field(ge=1, le=30)
    ch4_o2_ratio: float = Field(ge=1.4, le=2.5)
    co2_ch4_ratio: float = Field(ge=0, le=1.5)
    h2o_ch4_ratio: float = Field(ge=0, le=1.5)
    ghsv_per_h: float = Field(ge=1000, le=100000)
    catalyst: str
    catalyst_loading_wt_pct: float | None = Field(default=None, ge=0, le=20)
    n2_dilution_mol_pct: float | None = Field(default=None, ge=0, le=50)


class PredictResponse(BaseModel):
    predictions: dict[str, float]
    model_version: str


class MarketPricesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    natural_gas_price_usd_per_mmbtu: float
    syngas_price_usd_per_kmol: float
    carbon_credit_price_usd_per_tonne_co2e: float
    currency: Literal["USD"] = "USD"
    source: str
    is_mock: bool
    as_of: datetime
    cached: bool
    cache_ttl_seconds: int


class TeaAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    ch4_feed_kmol_per_h: float = Field(gt=0, le=1_000_000)
    natural_gas_price_usd_per_mmbtu: float = Field(ge=0, le=1_000)
    syngas_price_usd_per_kmol: float = Field(ge=0, le=1_000_000)
    carbon_credit_price_usd_per_tonne_co2e: float = Field(ge=0, le=100_000)
    co2_utilization_fraction: float = Field(default=DEFAULT_CO2_UTILIZATION_FRACTION, ge=0, le=1)
    capex_usd: float = Field(gt=0, le=1e12)
    opex_pct_of_capex_per_year: float = Field(
        default=DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR, ge=0, le=100
    )
    operating_hours_per_day: float = Field(default=DEFAULT_OPERATING_HOURS_PER_DAY, gt=0, le=24)
    operating_days_per_year: float = Field(default=DEFAULT_OPERATING_DAYS_PER_YEAR, gt=0, le=365)


class TeaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conditions: PredictRequest
    assumptions: TeaAssumptions


class TeaFinancials(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    syngas_kmol_per_day: float
    syngas_nm3_per_day: float
    syngas_revenue_usd_per_day: float
    co2_consumed_tonnes_per_day: float
    carbon_credit_value_usd_per_day: float
    total_revenue_usd_per_day: float
    feed_cost_usd_per_day: float
    opex_usd_per_day: float
    net_cash_flow_usd_per_day: float
    annual_net_cash_flow_usd: float
    roi_pct: float
    payback_years: float | None
    currency: Literal["USD"] = "USD"


class TeaResponse(BaseModel):
    predictions: dict[str, float]
    model_versions: dict[str, str]
    financials: TeaFinancials
    warnings: list[str]


ChatStatus = Literal["ok", "needs_input"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2_000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ChatErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str
    field: str | None = None
    value: float | str | None = None
    minimum: float | None = None
    maximum: float | None = None
    missing_fields: list[str] | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ChatStatus
    reply: str
    result: TeaResponse | None = None
    request_id: str

    @model_validator(mode="after")
    def result_matches_status(self) -> ChatResponse:
        if self.status == "ok" and self.result is None:
            raise ValueError("status 'ok' requires a result")
        if self.status == "needs_input" and self.result is not None:
            raise ValueError("status 'needs_input' must not include a result")
        return self
