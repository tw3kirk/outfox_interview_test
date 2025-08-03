import os
import numpy as np
from typing import List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from .models import Provider
from .database import SessionLocal
from .geocoding import geocode_zip_code, is_within_radius
import json
import threading

class OpenAIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found in environment variables")
            print("⚠️  Please create a .env file with OPENAI_API_KEY=your_api_key_here")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_cache = {}
        self.cache_lock = threading.Lock()
        
    def is_healthcare_related(self, query: str) -> bool:
        """Check if the query is related to healthcare/medical topics using OpenAI"""
        if not self.client:
            # If no OpenAI client, use simple keyword matching as fallback
            healthcare_keywords = [
                'hospital', 'medical', 'doctor', 'surgery', 'treatment', 'procedure',
                'health', 'medicine', 'patient', 'clinic', 'provider', 'rating',
                'cost', 'payment', 'diagnosis', 'disease', 'heart', 'cardiac',
                'cancer', 'emergency', 'specialist', 'nurse'
            ]
            query_lower = query.lower()
            return any(keyword in query_lower for keyword in healthcare_keywords)
        
        system_prompt = """
        You are a filter that determines if a user question is related to healthcare, medical procedures, 
        hospital information, medical costs, or provider ratings. 
        
        Return only 'YES' if the question is about:
        - Medical procedures, treatments, or surgeries
        - Hospital information, ratings, or quality
        - Healthcare costs, pricing, or payments
        - Provider comparisons or recommendations
        - Medical conditions or diagnoses
        - Healthcare facility locations or services
        
        Return only 'NO' if the question is about:
        - Weather, sports, politics, general knowledge
        - Technology, entertainment, food, travel (unless medical travel)
        - Personal life, relationships, education (unless medical education)
        - Any non-medical topics
        
        Respond with only 'YES' or 'NO'.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().upper()
            return result == "YES"
        except Exception as e:
            print(f"Error checking healthcare relevance: {e}")
            # Default to True to err on the side of caution
            return True
    
    def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text"""
        if not self.client:
            # Return empty list if no client available
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return []
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not a or not b:
            return 0.0
        
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        
        if a_norm == 0 or b_norm == 0:
            return 0.0
            
        return np.dot(a, b) / (a_norm * b_norm)
    
    def get_provider_embedding(self, provider_text: str) -> List[float]:
        """Get or calculate the embedding for a provider, using a cache to improve performance."""
        with self.cache_lock:
            if provider_text in self.embedding_cache:
                return self.embedding_cache[provider_text]

        # Calculate the embedding if not in cache
        embedding = self.get_embedding(provider_text)
        with self.cache_lock:
            self.embedding_cache[provider_text] = embedding
        return embedding

    def get_relevant_providers(self, query: str, limit: int = 10) -> List[Provider]:
        """
        Fast & reliable provider retrieval.
        1. Parse possible `drg`, `zip`, `radius_km` tokens from the question.
        2. Call the already-existing /providers endpoint (same process, no network hop)
           so we inherit all the geocoding / radius logic that is known to work.
        3. Return at most `limit` rows (already sorted by cost in the router).
        """
        # ---------- extract tokens ----------
        query_lc = query.lower()
        
        # Extract DRG codes (2-3 digits)
        drg = None
        for word in query_lc.split():
            if word.isdigit() and len(word) <= 3:
                drg = int(word)
                break
        
        # Extract zip codes (4-5 digits) - more robust extraction
        zip_code = None
        import re
        zip_pattern = r'\b\d{4,5}\b'  # Match 4-5 digit numbers as word boundaries
        zip_matches = re.findall(zip_pattern, query)
        if zip_matches:
            zip_code = int(zip_matches[0])
        
        # Extract radius (default 40km)
        radius_km = 40.0
        radius_keywords = ['km', 'kilometer', 'kilometers', 'radius', 'within']
        for word in query_lc.split():
            if word.replace('.', '').isdigit() and any(k in query_lc for k in radius_keywords):
                radius_km = float(word)
                break

        print(f"🔍 Extracted from query '{query}': drg={drg}, zip={zip_code}, radius_km={radius_km}")

        # ---------- delegate to existing SQL logic ----------
        # Use direct database query instead of TestClient to avoid circular imports
        db = SessionLocal()
        try:
            # Build query similar to /providers endpoint
            query = db.query(Provider)
            
            # Filter by DRG if provided
            if drg is not None:
                query = query.filter(Provider.ms_drg_definition == drg)
                print(f"🔍 Filtering by DRG: {drg}")
            
            # Get all providers that match the DRG filter
            providers = query.all()
            print(f"📊 Total providers in database: {len(providers)}")
            
            # Filter by zip code and radius if both are provided
            if zip_code is not None and radius_km is not None:
                print(f"🔍 Filtering by zip code: {zip_code} with radius: {radius_km}km")
                # Geocode the input zip code using Nominatim
                from .geocoding import geocode_zip_code_nominatim, is_within_radius
                zip_lat, zip_lon = geocode_zip_code_nominatim(str(zip_code).zfill(5))
                
                if zip_lat is None or zip_lon is None:
                    print(f"⚠️  Could not geocode zip code: {zip_code}")
                    return []
                
                print(f"✅ Geocoded zip {zip_code} to coordinates: {zip_lat}, {zip_lon}")
                
                # Filter providers by distance
                filtered_providers = []
                for provider in providers:
                    # Skip providers without coordinates
                    if provider.latitude is None or provider.longitude is None:
                        print(f"⚠️  Provider {provider.provider_name} has no coordinates")
                        continue
                    
                    # Check if provider is within radius
                    if is_within_radius(
                        zip_lat, zip_lon, 
                        provider.latitude, provider.longitude, 
                        radius_km
                    ):
                        filtered_providers.append(provider)
                        print(f"✅ Provider {provider.provider_name} is within radius")
                    else:
                        print(f"❌ Provider {provider.provider_name} is outside radius")
                
                providers = filtered_providers
                print(f"📊 Providers after radius filtering: {len(providers)}")
            
            # Sort by average_total_payments (ascending)
            providers = sorted(providers, key=lambda p: p.average_total_payments)
            
            # Limit results
            providers = providers[:limit]
            
            print(f"✅ Got {len(providers)} providers from database query")
            for provider in providers:
                print(f"   - {provider.provider_name} ({provider.provider_city}, {provider.provider_state}) - Rating: {provider.star_rating}/10")
            
            return providers
            
        except Exception as e:
            print(f"⚠️  Error in database query: {e}")
            return []
        finally:
            db.close()
    
    def generate_response(self, query: str, relevant_providers: List[Provider]) -> str:
        """Generate a response using OpenAI with provider context"""
        if not relevant_providers:
            return "I couldn't find any relevant provider information for your query. Please try rephrasing your question about medical procedures, costs, or hospital ratings."
        
        # Debug: Print the providers being used
        print(f"🔍 Generating response for query: {query}")
        print(f"📊 Number of relevant providers: {len(relevant_providers)}")
        for i, provider in enumerate(relevant_providers):
            print(f"   {i+1}. {provider.provider_name} ({provider.provider_city}, {provider.provider_state}) - Rating: {provider.star_rating}/10")
        
        # Prepare a concise context from relevant providers
        context = "Relevant providers:\n"
        for i, provider in enumerate(relevant_providers[:100], 1):  # Limit to top 100 providers
            context += f"{i}. {provider.provider_name} ({provider.provider_city}, {provider.provider_state}, {str(provider.provider_zip_code).zfill(5)})\n"
            context += f"   DRG: {provider.ms_drg_definition}, Rating: {provider.star_rating}/10\n"
            context += f"   Avg Total Payment: ${provider.average_total_payments}\n"
        
        if not self.client:
            # Fallback response without OpenAI
            return f"Based on the available data, here are the top providers for your query:\n\n{context}"
        
        system_prompt = """
        You are a helpful healthcare information assistant. Provide concise, accurate information about providers based on the data provided.
        Focus on ratings, costs, and location information. Keep responses brief and informative.
        
        If the user provides medical condition data, such as a DRG code, you should use that to filter the providers based on the relevant DRG code.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                max_tokens=1000,  # Reduced from 500
                temperature=0.7   # Reduced from 0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again later."
    
    async def ask(self, query: str) -> str:
        """Main method to handle user queries"""
        try:
            # Check if query is healthcare-related
            if not self.is_healthcare_related(query):
                return "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs or hospital ratings."
            
            # Get relevant providers using embeddings
            print(f"🔍 Processing query: {query}")
            relevant_providers = self.get_relevant_providers(query)
            print(f"📊 Found {len(relevant_providers)} relevant providers")
            
            # Generate response
            return self.generate_response(query, relevant_providers)
        except Exception as e:
            print(f"❌ Error in ask endpoint: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later."