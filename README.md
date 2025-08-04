# DeepSeaGuard Compliance Engine

A comprehensive backend service for processing live AUV telemetry, checking ISA (International Seabed Authority) violations, and pushing structured alerts and compliance logs to the frontend.

## Features

### 🗺️ Geo-fencing Service
- Load ISA zone GeoJSON into memory for fast spatial queries
- Real-time position checking against sensitive/restricted zones
- Support for Polygon and MultiPolygon geometries
- Configurable time limits per zone type

### ⚖️ Compliance Engine
- Define ISA rules (e.g., max 1 hour in sensitive zones)
- Track time spent per AUV in each zone
- Store every entry and exit with timestamp and zone ID
- Return status: "compliant", "warning", or "violation"

### 📊 Event Logging API
- POST `/compliance/log` endpoint for manual event logging
- Store all violations and compliance events in SQLite database
- Support querying logs by AUV, date, zone, or violation type
- Real-time statistics and reporting

### 🔌 Frontend Connection
- WebSocket support for live alert streaming
- RESTful API for zone status and compliance data
- Real-time zone status updates
- Comprehensive compliance reporting

## Tech Stack

- **Backend**: Python with FastAPI
- **Database**: SQLite (easily configurable for PostgreSQL/MySQL)
- **Geo Processing**: Shapely for geometric operations
- **Real-time**: WebSocket for live alerts
- **Validation**: Pydantic for data validation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
cd src
python database/init.py
```

This will:
- Create the database schema
- Populate with sample ISA zones (Jamaica area)
- Set up sample data for testing

### 3. Start the Server

```bash
cd src
python main.py
```

The server will start on `http://localhost:8000`

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Telemetry Processing

#### POST `/api/v1/telemetry/position`
Process AUV telemetry and check compliance:

```json
{
  "auv_id": "AUV_001",
  "latitude": 17.75,
  "longitude": -77.75,
  "depth": 150,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### POST `/api/v1/telemetry/batch`
Process multiple telemetry updates at once.

#### GET `/api/v1/telemetry/status/{auv_id}`
Get current status for an AUV.

### Compliance Management

#### POST `/api/v1/compliance/log`
Log a compliance event manually:

```json
{
  "auv_id": "AUV_001",
  "zone_id": "JM_SENSITIVE_001",
  "zone_name": "Jamaica Deep Sea Mining Sensitive Zone",
  "event_type": "entry",
  "status": "compliant",
  "latitude": 17.75,
  "longitude": -77.75,
  "depth": 150
}
```

#### GET `/api/v1/compliance/events`
Get compliance events with filtering options:
- `auv_id`: Filter by AUV ID
- `zone_id`: Filter by zone ID
- `event_type`: Filter by event type (entry, exit, violation, warning)
- `status`: Filter by status (compliant, warning, violation)
- `start_date`/`end_date`: Date range filtering

#### GET `/api/v1/compliance/report/{auv_id}`
Generate compliance report for an AUV.

#### GET `/api/v1/compliance/violations`
Get all violations with filtering.

#### GET `/api/v1/compliance/statistics`
Get compliance statistics for a date range.

### Zone Management

#### POST `/api/v1/zones`
Create a new ISA zone:

```json
{
  "zone_id": "NEW_ZONE_001",
  "zone_name": "New Protected Zone",
  "zone_type": "protected",
  "max_duration_hours": 2.0,
  "geojson_data": "{\"type\":\"Feature\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[...]]]}}"
}
```

#### GET `/api/v1/zones`
Get all zones with optional filtering.

#### POST `/api/v1/zones/upload`
Upload multiple zones from a GeoJSON file.

#### GET `/api/v1/zones/geojson`
Get all zones as a GeoJSON FeatureCollection.

## WebSocket API

### Connect to WebSocket
```
ws://localhost:8000/ws/alerts
```

### Message Types

#### Compliance Event
```json
{
  "type": "compliance_event",
  "auv_id": "AUV_001",
  "zone_id": "JM_SENSITIVE_001",
  "zone_name": "Jamaica Deep Sea Mining Sensitive Zone",
  "event_type": "violation",
  "status": "violation",
  "timestamp": "2024-01-15T10:30:00Z",
  "duration_minutes": 75.5,
  "violation_details": "Exceeded maximum duration of 1.0 hours in sensitive zone"
}
```

#### Zone Status Update
```json
{
  "type": "zone_status_update",
  "auv_id": "AUV_001",
  "zone_status": {
    "current_zones": [...],
    "position": {...},
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### Alert Message
```json
{
  "type": "compliance_alert",
  "auv_id": "AUV_001",
  "zone_id": "JM_SENSITIVE_001",
  "message": "Exceeded maximum duration of 1.0 hours in sensitive zone",
  "severity": "violation",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {...}
}
```

## Sample Data

The system comes with sample ISA zones in the Jamaica area:

1. **Jamaica Deep Sea Mining Sensitive Zone** (JM_SENSITIVE_001)
   - Max duration: 1 hour
   - Coordinates: Around Jamaica's deep sea mining area

2. **Jamaica Marine Protected Area** (JM_RESTRICTED_001)
   - Max duration: 30 minutes
   - Coordinates: Marine protected area

3. **Jamaica Coral Reef Protected Zone** (JM_PROTECTED_001)
   - Max duration: 2 hours
   - Coordinates: Coral reef protection area

## Testing

### Generate Sample Telemetry

```python
from utils.sample_data import generate_sample_telemetry

# Generate 30 minutes of telemetry
telemetry = generate_sample_telemetry("AUV_TEST_001", duration_minutes=30)

# Send to API
import requests
for data in telemetry:
    response = requests.post("http://localhost:8000/api/v1/telemetry/position", json=data)
    print(response.json())
```

### Generate Violation Scenario

```python
from utils.sample_data import generate_violation_scenario

# Generate telemetry that will trigger violations
violation_data = generate_violation_scenario()
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./deepseaguard.db
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
```

### Database Configuration

The system uses SQLite by default. To use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/deepseaguard
```

## Development

### Project Structure

```
src/
├── main.py                 # FastAPI application entry point
├── database/
│   ├── database.py        # Database models and configuration
│   └── init.py           # Database initialization script
├── models/
│   └── schemas.py        # Pydantic models for API
├── routers/
│   ├── compliance.py     # Compliance API endpoints
│   ├── telemetry.py      # Telemetry processing endpoints
│   └── zones.py          # Zone management endpoints
├── services/
│   ├── compliance_engine.py    # Core compliance logic
│   ├── geofencing_service.py   # Geo-fencing operations
│   └── websocket_manager.py    # WebSocket management
└── utils/
    └── sample_data.py    # Sample data generation
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
isort src/
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
RUN python src/database/init.py

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

1. **Database**: Use PostgreSQL for production
2. **Security**: Configure CORS origins properly
3. **Logging**: Set up proper logging configuration
4. **Monitoring**: Add health checks and metrics
5. **Scaling**: Consider using Redis for caching

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For questions or issues, please open a GitHub issue or contact the development team. 