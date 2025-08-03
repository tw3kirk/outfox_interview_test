# Providers API

A FastAPI backend application that provides healthcare provider data through a REST API, with PostgreSQL database integration and ETL processing from CSV data.

## Features

- FastAPI backend with Python 3.11
- PostgreSQL database with SQLAlchemy ORM
- Pydantic schemas for data validation
- ETL process to populate database from CSV
- Docker and Docker Compose support
- Local development setup with health checks
- **AI-powered query endpoint using OpenAI GPT-4o**
- **RAG (Retrieval-Augmented Generation) with embeddings**
- **Smart filtering for healthcare-related queries**

## API Endpoints

- `GET /` - Root endpoint
- `GET /providers` - Get all providers with optional filtering by DRG, zip code, and radius
- `POST /ask` - **AI-powered healthcare questions endpoint**
- `GET /health` - Health check

### Provider Search Endpoint

The `/providers` endpoint supports advanced filtering:

```bash
# Get all providers
curl "http://localhost:8000/providers"

# Filter by DRG (Diagnosis Related Group)
curl "http://localhost:8000/providers?drg=470"

# Filter by location and radius (requires all three parameters)
curl "http://localhost:8000/providers?drg=470&zip=10001&radius_km=40"
```

![hippo](https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2VncXA1dHFlNnhubHgzMndkMnM3MGhueTc5Z2RxeDRqcTVmNHpueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/hVrchVPAwcuk9movcT/giphy.gif)

**Query Parameters:**
- `drg` (optional): Diagnosis Related Group code
- `zip` (optional): Zip code to search from  
- `radius_km` (optional): Radius in kilometers from the zip code

### AI-Powered Ask Endpoint

The `/ask` endpoint allows natural language queries about healthcare providers using OpenAI GPT-4o with RAG (Retrieval-Augmented Generation).

**Endpoint:** `POST /ask`

**Request Body:**
```json
{
  "question": "Your healthcare-related question here"
}
```

**Response:**
```json
{
  "answer": "AI-generated response with relevant provider information"
}
```

#### Healthcare Query Examples

**Example 1: Best rated providers for procedures**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who has the best ratings for heart surgery near 10032?"}'
```

**Example 2: Cost comparisons**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the costs for hospital procedures in New York?"}'
```

**Example 3: Provider recommendations**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Find me the most affordable cardiac surgery providers with good ratings"}'
```

**Example 4: Location-based queries**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which hospitals in California have the highest star ratings?"}'
```

#### Non-Healthcare Queries

Non-healthcare related questions are automatically filtered out:

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the weather today?"}'

# Response:
{
  "answer": "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs or hospital ratings."
}
```

#### How the AI Works

1. **Query Filtering**: Uses AI to determine if questions are healthcare-related
2. **RAG with Embeddings**: Converts queries and provider data to embeddings for semantic matching
3. **Context Retrieval**: Finds the most relevant providers based on query similarity
4. **AI Response**: Uses GPT-4o to generate helpful responses with provider context
5. **Fallback Mode**: Works even without OpenAI API key using keyword matching

## Database Schema

The `providers` table contains the following columns:

- `id` (UUID, Primary Key) - Unique identifier for each record
- `provider_id` (String, Indexed) - Provider identifier from source data
- `provider_name` (String) - Name of the healthcare provider
- `provider_city` (String) - City where provider is located
- `provider_state` (String) - State where provider is located
- `provider_zip_code` (Integer, Indexed) - ZIP code of provider location
- `ms_drg_definition` (Integer) - Medicare Severity Diagnosis Related Group code
- `total_discharges` (Integer) - Number of patients discharged
- `average_covered_charges` (Decimal) - Average amount billed to insurance
- `average_total_payments` (Decimal) - Average total payments received
- `average_medicare_payments` (Decimal) - Average Medicare payments received
- `latitude` (Float, Nullable) - Geographic latitude for location-based queries
- `longitude` (Float, Nullable) - Geographic longitude for location-based queries
- `star_rating` (Integer) - Quality rating from 1-10 (higher is better)

## CSV Data Mapping

The ETL process maps the following CSV columns to database columns:

| CSV Column | Database Column |
|------------|-----------------|
| Rndrng_Prvdr_CCN | provider_id |
| Rndrng_Prvdr_Org_Name | provider_name |
| Rndrng_Prvdr_City | provider_city |
| Rndrng_Prvdr_State_Abrvtn | provider_state |
| Rndrng_Prvdr_Zip5 | provider_zip_code |
| DRG_Cd | ms_drg_definition |
| Tot_Dschrgs | total_discharges |
| Avg_Submtd_Cvrd_Chrg | average_covered_charges |
| Avg_Tot_Pymt_Amt | average_total_payments |
| Avg_Mdcr_Pymt_Amt | average_medicare_payments |

## Quick Start (Recommended)

The easiest way to run the application is using Docker Compose:

```bash
# Build and run with Docker Compose
docker compose up --build
```

This will:
- Start a PostgreSQL database container
- Build and start the FastAPI application container
- Run the ETL process on startup
- Make the API available on http://localhost:8000

## Local Development Setup

### Prerequisites

- Python 3.11
- PostgreSQL installed and running
- Virtual environment (recommended)

### PostgreSQL Installation and Setup

#### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Create postgres user with password
createuser -s postgres
psql postgres -c "ALTER USER postgres PASSWORD 'password';"

# Create the providers database
createdb -U postgres providers
```

#### Ubuntu/Debian
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Switch to postgres user and create database user
sudo -u postgres psql -c "CREATE USER postgres WITH SUPERUSER PASSWORD 'password';"
sudo -u postgres createdb providers
```

#### Windows
Download and install PostgreSQL from the official website: https://www.postgresql.org/download/windows/

After installation:
```sql
-- Connect to PostgreSQL as superuser and run:
CREATE USER postgres WITH SUPERUSER PASSWORD 'password';
CREATE DATABASE providers OWNER postgres;
```

### PostgreSQL User Setup (Important!)

If you're still having issues with empty database, follow these steps:

1. **Connect to PostgreSQL as superuser:**
```bash
# macOS
psql postgres

# Ubuntu/Debian
sudo -u postgres psql

# Windows
# Use pgAdmin or psql from PostgreSQL installation
```

2. **Create the postgres user with proper permissions:**
```sql
-- Create user if it doesn't exist
CREATE USER postgres WITH SUPERUSER PASSWORD 'password';

-- Grant all privileges
ALTER USER postgres WITH SUPERUSER;

-- Create the providers database
CREATE DATABASE providers OWNER postgres;

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE providers TO postgres;

-- Connect to the providers database
\c providers

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Exit
\q
```

3. **Test the connection:**
```bash
psql -h localhost -U postgres -d providers -c "SELECT 1;"
```

### OpenAI API Setup (Required for AI Features)

To use the `/ask` endpoint with full AI capabilities, you need to set up an OpenAI API key:

#### 1. Get an OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to the [API Keys page](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the generated API key (keep it secure!)

#### 2. Create Environment Configuration

Create a `.env` file in the project root directory:

```bash
# Create .env file
touch .env
```

Add your OpenAI API key to the `.env` file:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (for local development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/providers
```

**Important Notes:**
- Replace `your_openai_api_key_here` with your actual OpenAI API key
- The `.env` file is already in `.gitignore` to keep your API key secure
- Never commit your actual API key to version control

#### 3. Fallback Mode

The application works even without an OpenAI API key:
- **With API key**: Full AI capabilities with GPT-4o and embeddings
- **Without API key**: Basic keyword matching and structured responses

You'll see this warning if no API key is configured:
```
⚠️  OPENAI_API_KEY not found in environment variables
⚠️  Please create a .env file with OPENAI_API_KEY=your_api_key_here
```

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd outfox_interview_test
```

2. Create and activate a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Ensure PostgreSQL is running and accessible with:
   - Host: localhost
   - Port: 5432
   - User: postgres
   - Password: password
   - Database: providers

5. Run the application:
```bash
python run_local.py
```

The application will:
- Check if PostgreSQL is running
- Create the `providers` database if it doesn't exist
- Run the ETL process to populate the database
- Start the FastAPI server on http://localhost:8000

### API Documentation

Once the application is running, you can access:
- API documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Docker Deployment

### Using Docker Compose

1. **For AI features, create a `.env` file first:**
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

2. Build and run the application:
```bash
docker compose up --build
```

This will:
- Start a PostgreSQL database container
- Build and start the FastAPI application container
- Run the ETL process on startup
- Make the API available on http://localhost:8000
- Load environment variables from `.env` file (including OpenAI API key)

3. Stop the application:
```bash
docker compose down
```

### Using Docker Only

1. Build the Docker image:
```bash
docker build -t providers-api .
```

2. Run with a PostgreSQL database:
```bash
docker run -p 8000:8000 --env DATABASE_URL=postgresql://postgres:password@host.docker.internal:5432/providers providers-api
```

## Project Structure

```
outfox_interview_test/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── etl.py          # ETL process
│   ├── openai_service.py # AI service with RAG functionality
│   └── geocoding.py     # Geocoding utilities
├── MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv  # Source healthcare data
├── USZipsWithLatLon_20231227.csv          # ZIP code geocoding data
├── .env.example         # Environment variables template
├── requirements.txt     # Python dependencies
├── run_local.py        # Local development runner
├── run_etl.py          # Manual ETL runner
├── troubleshoot_db.py  # Database troubleshooting utility
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Environment Variables

The application uses environment variables for configuration. Create a `.env` file with:

- `OPENAI_API_KEY`: Your OpenAI API key for AI features (optional but recommended)
- `DATABASE_URL`: PostgreSQL connection string (default: postgresql://postgres:password@localhost:5432/providers)

**Example `.env` file:**
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
DATABASE_URL=postgresql://postgres:password@localhost:5432/providers
```

## Troubleshooting

### Empty Database Issues

If the database is created but empty after running the ETL:

1. **Check if the ETL process ran successfully:**
```bash
# Look for ETL output in the application logs
# You should see messages like:
# "✅ Successfully processed X records into the database"
```

2. **Verify database connection:**
```bash
psql -h localhost -U postgres -d providers -c "SELECT COUNT(*) FROM providers;"
```

3. **Check if tables exist:**
```bash
psql -h localhost -U postgres -d providers -c "\dt"
```

4. **Manually test the ETL process:**
```bash
# Install dependencies first
pip install -r requirements.txt

# Run ETL manually
python -c "from app.etl import run_etl; run_etl()"
```

5. **Check CSV file:**
```bash
# Verify CSV file exists and is readable
ls -la MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv
head -5 MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv
```

### SQLAlchemy 2.0 Compatibility

If you see errors like "Textual SQL expression should be explicitly declared as text()", this has been fixed in the latest version of the ETL script. The error occurs because SQLAlchemy 2.0 requires explicit text() wrapping for raw SQL queries.

### PostgreSQL Connection Issues

If you encounter PostgreSQL connection issues:

1. **Check if PostgreSQL is running:**
```bash
# macOS
brew services list | grep postgresql

# Ubuntu/Debian
sudo systemctl status postgresql

# Windows
# Check Services app for PostgreSQL service
```

2. **Start PostgreSQL if not running:**
```bash
# macOS
brew services start postgresql

# Ubuntu/Debian
sudo systemctl start postgresql

# Windows
# Start PostgreSQL service from Services
```

3. **Check PostgreSQL credentials and create user if needed:**
```sql
CREATE USER postgres WITH PASSWORD 'password';
ALTER USER postgres WITH SUPERUSER;
```

4. **Test PostgreSQL connection:**
```bash
psql -h localhost -U postgres -d postgres -c "SELECT 1;"
```

### CSV File Issues

Ensure the CSV file `MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv` is in the root directory of the project.

### Docker Issues

If Docker containers fail to start:

1. Check if ports are already in use:
```bash
lsof -i :8000
lsof -i :5432
```

2. Remove existing containers and volumes:
```bash
docker compose down -v
docker system prune -f
```

### Database Session Warnings

If you see SQLAlchemy warnings about session state, this is usually harmless and indicates that the ETL process is working correctly. The warnings occur when the session is rolled back after a successful commit.

## Development

### Adding New Endpoints

1. Add new routes in `app/main.py`
2. Create corresponding schemas in `app/schemas.py` if needed
3. Update this README with new endpoint documentation

### Database Migrations

The application uses SQLAlchemy's `create_all()` for table creation. For production, consider using Alembic for database migrations.

## License

This project is for interview purposes. 
