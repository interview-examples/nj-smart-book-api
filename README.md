# Smart Books API

## Overview
Smart Books API is a comprehensive RESTful API for managing books, built with Django and Django REST Framework. The API provides CRUD operations for books and enriches book data by integrating with multiple external APIs (Google Books, Open Library, NY Times). The application is containerized using Docker for easy setup and deployment.

## Features
- **Complete CRUD Operations**: Create, read, update, and delete books
- **Hybrid Data Enrichment**: 
  - Primary source: Google Books API
  - Fallback to Open Library if data is incomplete
  - Additional metadata from NY Times when available
  - Automatic merging of data from multiple sources for maximum completeness
- **Caching System**: Efficient caching of external API responses
- **Search Functionality**: Search books by title, author, or ISBN
- **Pagination**: Paginated results for better performance with large datasets
- **Swagger Documentation**: Interactive API documentation
- **Docker Integration**: Easy deployment with Docker and Docker Compose
- **CI/CD Pipeline**: Automated testing and deployment with GitHub Actions

## CI/CD Pipeline
The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that automates:
- **Code Quality**: Linting with flake8
- **Testing**: Running all tests with coverage reporting
- **Docker Build**: Building and pushing Docker images on successful tests
- **Deployment**: Automatic deployment to staging/production environments (configured via repository secrets)

The pipeline runs on:
- Push to `dev` and `master` branches
- Pull requests to `master`
- Manual workflow dispatch

## Architecture
The project follows a clean architecture pattern with separation of concerns:
- **Models**: Core data structures (Book, Author, BookISBN)
- **Services**: Business logic and external API integration
  - Base API Service: Common functionality for all external API services
  - Specialized Services: Google Books, Open Library, NY Times
  - Enrichment Service: Orchestrates data collection from multiple sources
  - Caching Decorators: Handle caching of external API responses
- **Serializers**: Data transformation and validation
- **Views**: API endpoints and request handling
- **Tests**: Comprehensive test suite for all components

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- API keys for external services (optional, but recommended for full functionality)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smart-books-api.git
cd smart-books-api
```

2. Create a `.env` file in the project root with your API keys:
```
GOOGLE_BOOKS_API_KEY=your_google_api_key
NYTIMES_API_KEY=your_nytimes_api_key
```

3. Build and run the Docker containers:
```bash
docker-compose up --build
```

4. The API will be available at http://localhost:8000/api/

## API Endpoints

### Books
- `GET /api/v1/books/`: List all books (with pagination)
- `POST /api/v1/books/`: Create a new book
- `GET /api/v1/books/{id}/`: Retrieve a specific book with enriched data
- `PUT /api/v1/books/{id}/`: Update a specific book
- `PATCH /api/v1/books/{id}/`: Partially update a specific book
- `DELETE /api/v1/books/{id}/`: Delete a specific book
- `GET /api/v1/books/search/?q={query}`: Search books by title, author, or ISBN
- `GET /api/v1/books/isbn/{isbn}/`: Retrieve a book by its ISBN with enriched data

### Enrichment
- `GET /api/v1/enrichment/enrich_by_isbn/?isbn={isbn}`: Get enriched data for a book by ISBN
- `POST /api/v1/enrichment/search_external/`: Search for books in external APIs

### Statistics
- `GET /api/v1/stats/`: Get statistics about books in the database

## Documentation
- Swagger UI: [/api/v1/docs/](http://localhost:8000/api/v1/docs/)
- OpenAPI Schema: [/api/v1/schema/](http://localhost:8000/api/v1/schema/)

## Running Tests
To run the test suite:
```bash
docker-compose exec web python manage.py test
```

For specific test modules:
```bash
docker-compose exec web python manage.py test books.tests.services
```

## Caching
The API implements a caching system to minimize calls to external APIs:
- Default cache timeout: 24 hours
- Cache invalidation on book updates
- Custom cache decorators for different external API endpoints
- Cache keys based on ISBN and query parameters

## External APIs Integration
The API implements a smart hybrid approach to data enrichment, combining multiple sources for maximum data completeness:

### Data Enrichment Strategy
1. **Primary Source - Google Books**:
   - First attempt to fetch complete book data
   - Includes high-quality metadata and cover images

2. **Fallback to Open Library**:
   - If Google Books data is incomplete or unavailable
   - Provides alternative metadata and cover images
   - Often contains additional publication details

3. **Supplemental Data from NY Times**:
   - Adds professional book reviews
   - Includes bestseller list information
   - Provides additional credibility indicators

The system automatically merges data from all available sources, prioritizing the most complete and reliable information for each field.

### Enriched Data Structure
When retrieving a book with enriched data, the response includes combined information from all available sources:

- **Basic Information**:
  - `title` (from Google Books or Open Library)
  - `authors` (combined from all sources)
  - `description` (longest available description)
  - `published_date` (most specific date available)

- **Extended Metadata**:
  - `publisher` (from primary source)
  - `page_count` (highest available)
  - `categories` (combined from all sources)
  - `language` (preferred from Google Books, fallback to Open Library)

- **Media & Links**:
  - `cover_url` (highest resolution available)
  - `preview_link` (when available)
  - `reviews` (from NY Times when available)

- **Source Information**:
  - `data_sources`: List of sources used for enrichment
  - `enrichment_status`: Indicates which sources contributed data

This hybrid approach ensures the most complete and accurate book information possible, automatically handling cases where data might be missing from any single source.

## ISBN Support
The API fully supports both ISBN-10 and ISBN-13 formats:

- Book creation accepts either ISBN-10 or ISBN-13
- ISBN can be entered with or without hyphens (e.g., "978-3-16-148410-0" or "9783161484100")
- When retrieving books by ISBN, you can use either format
- Book enrichment works with both formats, automatically trying alternatives if available

## Production Deployment

### Redis Optimization
When deploying to production, you might see warnings from Redis about memory overcommit settings. To optimize Redis performance and prevent potential issues with background saves and replication:

```bash
# Set the vm.overcommit_memory kernel parameter to 1
echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf

# Apply the change without restarting
sysctl vm.overcommit_memory=1
```

This setting allows the operating system to allocate more memory than physically available, which is required for Redis to work optimally with its fork-based persistence model.

### Other Recommendations
- Use a proper reverse proxy (Nginx, Apache) in front of the application
- Configure rate limiting at the proxy level
- Set up proper SSL/TLS termination
- Use environment variables for all sensitive configuration

## Development
For development purposes, you can use the development environment:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

## Assumptions and Design Choices
- **Framework**: Django with Django REST Framework for robust API development
- **Database**: PostgreSQL for production, SQLite for development
- **Caching**: Django's cache framework with Redis backend
- **API Documentation**: drf-spectacular for OpenAPI schema generation
- **Testing**: Django's test framework with unittest.mock for external API mocking
- **ISBN Validation**: Custom validation for ISBN-10 and ISBN-13 formats

## License
This project is licensed under the MIT License - see the LICENSE file for details.
