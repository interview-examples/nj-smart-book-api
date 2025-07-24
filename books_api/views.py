"""
Simple views for API documentation without using drf-spectacular.
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def api_schema(request):
    """
    Simple view that returns a complete API schema.
    """
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "Smart Books API",
            "version": "1.0.0",
            "description": "RESTful API for managing books with enrichment and caching",
        },
        "tags": [
            {"name": "books", "description": "Book management endpoints"},
            {"name": "enrichment", "description": "Book data enrichment endpoints"},
            {"name": "statistics", "description": "Book statistics endpoints"},
        ],
        "paths": {
            # Book endpoints
            "/api/v1/books/": {
                "get": {
                    "operationId": "books_list",
                    "summary": "List all books",
                    "description": "Get a paginated list of all books with filtering options",
                    "tags": ["books"],
                    "parameters": [
                        {
                            "name": "search",
                            "in": "query",
                            "description": "Search by title, author or ISBN",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "author",
                            "in": "query",
                            "description": "Filter by author name",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "year",
                            "in": "query",
                            "description": "Filter by publication year",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number for pagination",
                            "required": False,
                            "schema": {"type": "integer", "default": 1},
                        },
                        {
                            "name": "page_size",
                            "in": "query",
                            "description": "Number of items per page",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "default": 20,
                                "maximum": 100,
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "List of books",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "count": {"type": "integer"},
                                            "next": {
                                                "type": "string",
                                                "format": "uri",
                                                "nullable": True,
                                            },
                                            "previous": {
                                                "type": "string",
                                                "format": "uri",
                                                "nullable": True,
                                            },
                                            "results": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Book"
                                                },
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "books_create",
                    "summary": "Create a book",
                    "description": "Create a new book entry",
                    "tags": ["books"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BookCreate"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Book created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Book"}
                                }
                            },
                        },
                        "400": {"description": "Bad request - validation error"},
                    },
                },
            },
            "/api/v1/books/{id}/": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "description": "ID of the book",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "get": {
                    "operationId": "books_retrieve",
                    "summary": "Get book details",
                    "description": "Get detailed information about a specific book, including enriched data",
                    "tags": ["books"],
                    "responses": {
                        "200": {
                            "description": "Book details with enriched data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/EnrichedBook"
                                    }
                                }
                            },
                        },
                        "404": {"description": "Book not found"},
                    },
                },
                "put": {
                    "operationId": "books_update",
                    "summary": "Update book",
                    "description": "Update all fields of a specific book",
                    "tags": ["books"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BookCreate"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Book updated",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Book"}
                                }
                            },
                        },
                        "404": {"description": "Book not found"},
                    },
                },
                "patch": {
                    "operationId": "books_partial_update",
                    "summary": "Partial update",
                    "description": "Update specific fields of a book",
                    "tags": ["books"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BookCreate"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Book updated",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Book"}
                                }
                            },
                        },
                        "404": {"description": "Book not found"},
                    },
                },
                "delete": {
                    "operationId": "books_delete",
                    "summary": "Delete book",
                    "description": "Delete a specific book",
                    "tags": ["books"],
                    "responses": {
                        "204": {"description": "Book deleted successfully"},
                        "404": {"description": "Book not found"},
                    },
                },
            },
            "/api/v1/books/isbn/{isbn}/": {
                "get": {
                    "operationId": "books_get_by_isbn",
                    "summary": "Get a book by ISBN",
                    "description": "Retrieve a specific book by its ISBN-10 or ISBN-13 with enriched data from external sources",
                    "tags": ["books"],
                    "parameters": [
                        {
                            "name": "isbn",
                            "in": "path",
                            "description": "ISBN-10 or ISBN-13 of the book (with or without hyphens)",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/EnrichedBook"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "Book not found",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "error": {
                                                "type": "string",
                                                "example": "Book not found",
                                            }
                                        },
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/api/v1/books/search/": {
                "get": {
                    "operationId": "books_search",
                    "summary": "Search books",
                    "description": "Search books by title, author or ISBN",
                    "tags": ["books"],
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "description": "Search query for title, author or ISBN",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number for pagination",
                            "required": False,
                            "schema": {"type": "integer", "default": 1},
                        },
                        {
                            "name": "page_size",
                            "in": "query",
                            "description": "Number of items per page",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "default": 20,
                                "maximum": 100,
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Search results",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "count": {"type": "integer"},
                                            "next": {
                                                "type": "string",
                                                "format": "uri",
                                                "nullable": True,
                                            },
                                            "previous": {
                                                "type": "string",
                                                "format": "uri",
                                                "nullable": True,
                                            },
                                            "results": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Book"
                                                },
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            # Enrichment endpoints
            "/api/v1/enrichment/enrich_by_isbn/": {
                "get": {
                    "operationId": "enrichment_by_isbn",
                    "summary": "Enrich by ISBN",
                    "description": "Enrich book data using ISBN from external sources",
                    "tags": ["enrichment"],
                    "parameters": [
                        {
                            "name": "isbn",
                            "in": "query",
                            "description": "ISBN of the book to enrich",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Enriched book data",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "400": {"description": "ISBN parameter is missing"},
                        "404": {"description": "Failed to enrich book data"},
                    },
                }
            },
            "/api/v1/enrichment/search_external/": {
                "post": {
                    "operationId": "search_external",
                    "summary": "Search external sources",
                    "description": "Search for books in external sources",
                    "tags": ["enrichment"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Search query",
                                        }
                                    },
                                    "required": ["query"],
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Search results from external sources",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    }
                                }
                            },
                        },
                        "400": {"description": "Query parameter is missing"},
                    },
                }
            },
            # Statistics endpoint
            "/api/v1/stats/": {
                "get": {
                    "operationId": "book_stats",
                    "summary": "Book statistics",
                    "description": "Get statistics about books in the database",
                    "tags": ["statistics"],
                    "responses": {
                        "200": {
                            "description": "Book statistics",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "total_books": {"type": "integer"},
                                            "total_authors": {"type": "integer"},
                                            "books_by_year": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "integer"
                                                },
                                            },
                                            "most_common_genres": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "genre": {"type": "string"},
                                                        "count": {"type": "integer"},
                                                    },
                                                },
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Book": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "title": {"type": "string"},
                        "isbn": {"type": "string"},
                        "description": {"type": "string", "nullable": True},
                        "published_date": {"type": "string", "format": "date"},
                        "authors": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "isbn", "authors"],
                },
                "BookCreate": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "isbn": {"type": "string"},
                        "description": {"type": "string", "nullable": True},
                        "published_date": {"type": "string", "format": "date"},
                        "authors": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "isbn", "authors"],
                },
                "EnrichmentData": {
                    "type": "object",
                    "properties": {
                        "external_title": {"type": "string", "nullable": True},
                        "external_subtitle": {"type": "string", "nullable": True},
                        "external_authors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "nullable": True,
                        },
                        "external_description": {"type": "string", "nullable": True},
                        "publisher": {"type": "string", "nullable": True},
                        "publication_year": {"type": "string", "nullable": True},
                        "page_count": {"type": "integer", "nullable": True},
                        "language": {"type": "string", "nullable": True},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "nullable": True,
                        },
                        "thumbnail": {"type": "string", "nullable": True},
                        "preview_link": {"type": "string", "nullable": True},
                        "rating": {
                            "type": "number",
                            "format": "float",
                            "nullable": True,
                        },
                        "reviews_count": {"type": "integer", "nullable": True},
                        "ny_times_review": {"type": "string", "nullable": True},
                    },
                },
                "EnrichedBook": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "title": {"type": "string"},
                        "isbn": {"type": "string"},
                        "description": {"type": "string", "nullable": True},
                        "published_date": {"type": "string", "format": "date"},
                        "authors": {"type": "array", "items": {"type": "string"}},
                        "enriched_data": {
                            "$ref": "#/components/schemas/EnrichmentData"
                        },
                    },
                    "required": ["title", "isbn", "authors"],
                },
            }
        },
    }

    return JsonResponse(schema)


def api_docs(request):
    """
    Simple HTML view for API documentation.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart Books API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4/swagger-ui.css">
        <style>
            body {
                margin: 0;
                padding: 0;
            }
            .swagger-ui .topbar {
                background-color: #2c3e50;
            }
            .swagger-ui .info .title {
                color: #2c3e50;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
        <script>
            const ui = SwaggerUIBundle({
                url: "/api/v1/schema/",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis
                ],
                layout: "BaseLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1
            })
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)
