# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-alpha-api] - 2026-05-19

### Added
- Django 4.2 + Django REST Framework 3.15.1
- drf-spectacular for OpenAPI 3.0 schema generation
- OpenAPI validation on CI/CD (100% compliance enforced)
- Complete trip planning endpoint (POST /api/v1/plan-route/)
- OSRM integration for route calculation
- Nominatim integration for geocoding
- HOS (Hours of Service) simulation engine
- ELD (Electronic Logging Device) logbook generation
- Multi-day trip support with automatic stop detection
- Comprehensive API documentation (Swagger UI at /api/docs/)

### Features
- **Trip Planning API** - Input: current location, pickup, dropoff, cycle hours used
- **Route Calculation** - Returns 2-leg routes with distance and duration
- **HOS Simulation** - Calculates valid duty status transitions per FMCSA rules
- **ELD Logbook Generation** - Multi-day logbook with events, rest stops, fuel stops
- **Map Markers** - Start, pickup, dropoff, fuel, and rest stop markers
- **Trip Summary** - Total distance, hours, drive time, number of stops

### Testing
- 8 unit tests covering OpenAPI validation, routing, HOS simulation
- 100% endpoint schema compliance validation
- pytest fixtures for mock data
- CI/CD validation of OpenAPI spec against generated schema

### Documentation
- Comprehensive README with setup and API integration
- OpenAPI specification (YAML)
- Architecture documentation
- API endpoint documentation
- Contributing guidelines

### Fixed
- Serializer field names aligned with OpenAPI spec (cycle_hours_used)
- Marker types match spec enums (start, pickup, dropoff, fuel, rest)
- TripSummary structure with all required fields
- LogbookEvent timing (start_minute, duration_minutes)
- LogbookDay numbering (day, events)
- cycle_hours_used corrected to FloatField (was documented as IntegerField)
- route_coordinates coordinate order corrected to [lon, lat] GeoJSON order (was documented as [lat, lon])
- trip_summary.legs field name corrected (was number_of_legs in README example); value is always 2
- Added SLEEPER_BERTH to LogbookEvent.status enum; SLEEPER reserved for future split-berth
- Location field max_length corrected to 500 (was documented as 255)

### Dependencies
- Django: 4.2.x
- djangorestframework: 3.15.1
- drf-spectacular: 0.27.x
- pyyaml: 6.x
- requests: 2.31.x (for external APIs)
- pytest: 7.x
- python-dotenv: 1.x

## Upgrading from Previous Versions

This is the first alpha release. No upgrades needed.

## Future Releases

### v1.0.0-beta-api (Planned)
- Error handling with circuit breakers
- Rate limiting and request throttling
- Enhanced logging and monitoring
- Database persistence of trip plans

### v1.0.0-api (Planned)
- Full production readiness
- Authentication and authorization
- API versioning (v2, etc.)
- Comprehensive error handling
- Performance optimizations
