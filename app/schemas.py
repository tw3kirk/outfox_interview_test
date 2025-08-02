from pydantic import BaseModel
from typing import List
from uuid import UUID

class ProviderBase(BaseModel):
    provider_id: str
    provider_name: str
    provider_city: str
    provider_state: str
    provider_zip_code: str
    ms_drg_definition: str
    total_discharges: int
    average_covered_charges: float
    average_total_payments: float
    average_medicare_payments: float

class Provider(ProviderBase):
    id: UUID
    
    class Config:
        from_attributes = True

class ProviderList(BaseModel):
    providers: List[Provider] 