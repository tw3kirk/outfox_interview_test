from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn

from .database import get_db, engine
from .models import Provider, Base
from .schemas import Provider as ProviderSchema, AskRequest, AskResponse
from .etl import run_etl
from .geocoding import geocode_zip_code_nominatim, is_within_radius
from .openai_service import OpenAIService

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Providers API", description="API for managing healthcare providers data")

# Initialize OpenAI service
openai_service = OpenAIService()

@app.on_event("startup")
async def startup_event():
    """Run ETL process on startup"""
    print("Running ETL process on startup...")
    run_etl()

@app.get("/")
async def root():
    return {"message": "Providers API is running"}

@app.get("/providers", response_model=List[ProviderSchema])
async def get_providers(
    drg: Optional[int] = Query(None, description="Diagnosis Related Group code"),
    zip: Optional[int] = Query(None, description="Zip code to search from"),
    radius_km: Optional[float] = Query(None, description="Radius in kilometers"),
    db: Session = Depends(get_db)
):
    """Get providers with optional filtering by DRG, zip code, and radius. Results are sorted by average_total_payments ascending."""
    
    # Start with all providers
    query = db.query(Provider)
    
    # Filter by DRG if provided
    if drg is not None:
        query = query.filter(Provider.ms_drg_definition == drg)
    
    # Get all providers that match the DRG filter
    providers = query.all()
    
    # Filter by zip code and radius if both are provided
    if zip is not None and radius_km is not None:
        # Geocode the input zip code using Nominatim
        zip_lat, zip_lon = geocode_zip_code_nominatim(str(zip).zfill(5))
        
        if zip_lat is None or zip_lon is None:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not geocode zip code: {zip}"
            )
        
        # Filter providers by distance
        filtered_providers = []
        for provider in providers:
            # Skip providers without coordinates
            if provider.latitude is None or provider.longitude is None:
                continue
            
            # Check if provider is within radius
            if is_within_radius(
                zip_lat, zip_lon, 
                provider.latitude, provider.longitude, 
                radius_km
            ):
                filtered_providers.append(provider)
        
        providers = filtered_providers
    
    # Sort by average_total_payments (ascending)
    providers = sorted(providers, key=lambda p: p.average_total_payments)
    
    return providers

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask questions about healthcare providers using AI"""
    try:
        print(f"🔍 Received question: {request.question}")
        
        # Validate request
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        # Call OpenAI service
        print("📝 Calling OpenAI service...")
        answer = await openai_service.ask(request.question)
        print(f"✅ Generated answer: {answer}")
        
        return AskResponse(answer=answer)
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Error in ask endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail="I'm having trouble processing your question right now. Please try again later."
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 