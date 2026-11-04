from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid") # Reject unexpected fields
    
    temperature_c: float = Field(ge=500, le=1000)
    pressure_bar: float = Field(ge=1, le=30)
    ch4_o2_ratio: float = Field(ge=1.4, le=2.5)
    co2_ch4_ratio: float = Field(ge=0, le=1.5)
    h2o_ch4_ratio: float = Field(ge=0, le=1.5)
    ghsv_per_h: float = Field(ge=1000, le=100000)
    catalyst: str
    catalyst_loading_wt_pct: Optional[float] = Field(default=None, ge=0, le=20)
    n2_dilution_mol_pct: Optional[float] = Field(default=None, ge=0, le=50)

class PredictResponse(BaseModel):
    predictions: dict[str, float]
    model_version: str