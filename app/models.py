from sqlalchemy import Column, String, Integer, Float, Numeric
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .database import Base

class Provider(Base):
    __tablename__ = "providers"
    
    # Use UUID as primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    provider_id = Column(String, nullable=False, index=True)
    provider_name = Column(String, nullable=False)
    provider_city = Column(String, nullable=False)
    provider_state = Column(String, nullable=False)
    provider_zip_code = Column(Integer, nullable=False, index=True)
    ms_drg_definition = Column(Integer, nullable=False)
    total_discharges = Column(Integer, nullable=False)
    average_covered_charges = Column(Numeric(precision=18, scale=2), nullable=False)
    average_total_payments = Column(Numeric(precision=18, scale=2), nullable=False)
    average_medicare_payments = Column(Numeric(precision=18, scale=2), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True) 