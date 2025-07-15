# Smart Books API

## Overview
Smart Books API is a comprehensive RESTful API for managing books, built with Django and Django REST Framework. The API provides CRUD operations for books and enriches book data by integrating with multiple external APIs (Google Books, Open Library, NY Times). The application is containerized using Docker for easy setup and deployment.

## Features
- **Complete CRUD Operations**: Create, read, update, and delete books
- **Data Enrichment**: Automatically enrich book data from external sources:
  - Google Books API: Book details, cover images, and categories
  - Open Library API: Additional book metadata
  - NY Times API: Book reviews and bestseller lists
- **Caching System**: Efficient caching of external API responses to minimize network calls
- **Search Functionality**: Search books by title, author, or ISBN
- **Pagination**: Paginated results for better performance with large datasets
- **Swagger Documentation**: Interactive API documentation
- **Docker Integration**: Easy deployment with Docker and Docker Compose

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
- Swagger UI: `/api/v1/docs/`
- OpenAPI Schema: `/api/v1/schema/`

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
The API integrates with the following external services:

### Google Books API
- Book details (title, author, description)
- Cover images
- Categories and page count
- Preview links

### Open Library API
- Additional book metadata
- Alternative cover images
- Publication information

### NY Times API
- Book reviews
- Bestseller lists

## Enriched Data Structure
When retrieving a book with enriched data (either via `GET /api/v1/books/{id}/` or `GET /api/v1/books/isbn/{isbn}/`), the response includes an `enriched_data` object with the following fields:

- `external_title`: Book title from external source
- `external_subtitle`: Book subtitle (if available)
- `external_authors`: List of authors from external source
- `external_description`: Book description (may be more comprehensive than internal description)
- `publisher`: Publisher name
- `publication_year`: Year of publication
- `page_count`: Number of pages
- `language`: Language code (e.g., 'en', 'fr', 'ru')
- `categories`: List of book categories/genres
- `thumbnail`: URL to book cover thumbnail
- `preview_link`: URL to book preview (if available)
- `rating`: Average rating (0-5 scale)
- `reviews_count`: Number of reviews
- `ny_times_review`: NY Times review snippet (if available)
- `data_source`: Source of the enriched data (e.g., 'Google Books', 'Open Library')

Note that some fields may be `null` if the data is not available from external sources.

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
