from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

class ProviderBase(BaseModel):
    provider_id: str
    provider_name: str
    provider_city: str
    provider_state: str
    provider_zip_code: int
    ms_drg_definition: int
    total_discharges: int
    average_covered_charges: Decimal
    average_total_payments: Decimal
    average_medicare_payments: Decimal
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    star_rating: int

class Provider(ProviderBase):
    id: UUID
    
    class Config:
        from_attributes = True

class ProviderList(BaseModel):
    providers: List[Provider] 