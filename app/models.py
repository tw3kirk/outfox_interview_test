from sqlalchemy import Column, String, Integer, Float
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
    provider_zip_code = Column(String, nullable=False)
    ms_drg_definition = Column(String, nullable=False)
    total_discharges = Column(Integer, nullable=False)
    average_covered_charges = Column(Float, nullable=False)
    average_total_payments = Column(Float, nullable=False)
    average_medicare_payments = Column(Float, nullable=False) 