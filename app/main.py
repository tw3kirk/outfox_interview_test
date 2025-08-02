from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from .database import get_db, engine
from .models import Provider, Base
from .schemas import Provider as ProviderSchema
from .etl import run_etl

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Providers API", description="API for managing healthcare providers data")

@app.on_event("startup")
async def startup_event():
    """Run ETL process on startup"""
    print("Running ETL process on startup...")
    run_etl()

@app.get("/")
async def root():
    return {"message": "Providers API is running"}

@app.get("/providers", response_model=List[ProviderSchema])
async def get_providers(db: Session = Depends(get_db)):
    """Get all providers from the database"""
    providers = db.query(Provider).all()
    return providers

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 