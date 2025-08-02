import os
import numpy as np
from typing import List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from .models import Provider
from .database import SessionLocal
from .geocoding import geocode_zip_code_nominatim, is_within_radius
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
        """Get providers most relevant to the query using database filtering, geocoding, and radius search"""
        db = SessionLocal()
        try:
            # Extract potential filters from the query
            query_lower = query.lower()
            
            # Try to extract DRG code from query
            drg_filter = None
            for word in query_lower.split():
                if word.isdigit() and len(word) <= 3:  # DRG codes are typically 2-3 digits
                    drg_filter = int(word)
                    break
            
            # Try to extract zip code from query
            zip_filter = None
            for word in query_lower.split():
                if word.isdigit() and (len(word) == 4 or len(word) == 5):  # Zip codes can be 4 or 5 digits
                    zip_filter = int(word)
                    break
            
            # Build database query with filters
            db_query = db.query(Provider)
            
            if drg_filter:
                db_query = db_query.filter(Provider.ms_drg_definition == drg_filter)
            
            # Get filtered providers
            providers = db_query.all()
            
            # If no providers found with DRG filter, try broader search
            if not providers:
                providers = db.query(Provider).all()
            
            # If still no providers, return empty list
            if not providers:
                return []
            
            # Apply radius filtering if zip code is found
            if zip_filter:
                # Geocode the input zip code
                zip_lat, zip_lon = geocode_zip_code_nominatim(str(zip_filter).zfill(5))
                
                if zip_lat and zip_lon:
                    print(f"🔍 Geocoded zip {zip_filter} to coordinates: {zip_lat}, {zip_lon}")
                    
                    # Default radius of 40km if not specified in query
                    radius_km = 40.0
                    
                    # Check if radius is mentioned in query
                    radius_keywords = ['within', 'radius', 'km', 'kilometers', 'miles']
                    for word in query_lower.split():
                        if word.isdigit() and any(keyword in query_lower for keyword in radius_keywords):
                            radius_km = float(word)
                            break
                    
                    print(f"📍 Using radius: {radius_km}km")
                    print(f"📊 Total providers before radius filtering: {len(providers)}")
                    
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
                            print(f"✅ Provider {provider.provider_name} ({provider.provider_city}, {provider.provider_state}) is within radius")
                        else:
                            print(f"❌ Provider {provider.provider_name} ({provider.provider_city}, {provider.provider_state}) is outside radius")
                    
                    print(f"📊 Providers after radius filtering: {len(filtered_providers)}")
                    providers = filtered_providers
                else:
                    print(f"⚠️  Could not geocode zip code: {zip_filter}")
            
            # Use simple keyword matching for scoring
            keyword_matches = []
            
            for provider in providers:
                score = 0
                
                # Check for DRG matches
                if drg_filter and provider.ms_drg_definition == drg_filter:
                    score += 10
                
                # Check for zip code matches
                if zip_filter and provider.provider_zip_code == zip_filter:
                    score += 15  # Increased from 8
                
                # Check for location matches
                if provider.provider_city.lower() in query_lower or provider.provider_state.lower() in query_lower:
                    score += 5  # Increased from 3
                
                # Check for provider name matches
                if any(word.lower() in provider.provider_name.lower() for word in query.split()):
                    score += 2
                
                # Check for rating-related keywords
                if any(word in query_lower for word in ['rating', 'star', 'best', 'top']):
                    score += provider.star_rating * 0.3  # Reduced from 0.5
                
                # Higher star rating gets bonus (but not as much as location)
                score += provider.star_rating * 0.1
                
                # Bonus for providers that passed radius filtering (they're in the right area)
                if zip_filter:
                    score += 20  # High bonus for being in the correct area
                
                keyword_matches.append((provider, score))
            
            # Sort by score and star rating
            keyword_matches.sort(key=lambda x: (x[1], x[0].star_rating), reverse=True)
            return [provider for provider, score in keyword_matches[:limit]]
            
        except Exception as e:
            print(f"Error getting relevant providers: {e}")
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
        for i, provider in enumerate(relevant_providers[:3]):
            print(f"   {i+1}. {provider.provider_name} ({provider.provider_city}, {provider.provider_state}) - Rating: {provider.star_rating}/10")
        
        # Prepare a concise context from relevant providers
        context = "Relevant providers:\n"
        for i, provider in enumerate(relevant_providers[:5], 1):  # Limit to top 5 providers
            context += f"{i}. {provider.provider_name} ({provider.provider_city}, {provider.provider_state})\n"
            context += f"   DRG: {provider.ms_drg_definition}, Rating: {provider.star_rating}/10\n"
            context += f"   Avg Total Payment: ${provider.average_total_payments}\n"
        
        if not self.client:
            # Fallback response without OpenAI
            return f"Based on the available data, here are the top providers for your query:\n\n{context}"
        
        system_prompt = """
        You are a helpful healthcare information assistant. Provide concise, accurate information about providers based on the data provided.
        Focus on ratings, costs, and location information. Keep responses brief and informative.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                max_tokens=300,  # Reduced from 500
                temperature=0.5   # Reduced from 0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again later."
    
    async def ask(self, query: str) -> str:
        """Main method to handle user queries"""
        # Check if query is healthcare-related
        if not self.is_healthcare_related(query):
            return "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs or hospital ratings."
        
        # Get relevant providers using embeddings
        relevant_providers = self.get_relevant_providers(query)
        
        # Generate response
        return self.generate_response(query, relevant_providers)