# Books API Project
## Overview
This project is a Django-based RESTful API for managing books. It includes CRUD operations for books and enriches book data using the Open Library API. The application is containerized using Docker for easy setup and deployment.

##Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/book_project.git
cd book_project
```

2.Build and run the Docker containers:
```bash
docker-compose up --build
```

## Access the API:
The API will be available at http://localhost:8000.

## Running Tests
To run the unit tests, use the following command:
```bash
docker-compose exec web python manage.py test
```

## API Endpoints
* Basic API path: /api/v1
* GET /books/: Retrieve a list of all books.
* POST /books/: Create a new book.
* GET /books//: Retrieve details of a specific book.
* PUT /books//: Update a specific book.
* DELETE /books//: Delete a specific book.
* GET /api/v1/schema/: Retrieve the OpenAPI schema *(download .yml)*
* GET /api/v1/docs/: Access the Swagger interactive documentation for the API.

Each book response includes enriched data such as cover URL, page count, and genres fetched from Open Library.

## Assumptions and Choices
- Framework: Django with Django REST Framework for building the API.
- Database: PostgreSQL, managed via Docker.
- Data Enrichment: Using Open Library API for fetching additional book information based on ISBN.
- Caching: Implemented using Django's cache framework with a custom decorator. Cache expires after 24 hours and is invalidated on book update or delete.
- Testing: Unit tests cover CRUD operations, data enrichment, and caching logic using Django's test framework and the responses library for mocking external API calls.
