"""
Custom schema views to fix drf-spectacular issues with authentication.
"""
from typing import Any, Dict, List, Optional

from django.http import JsonResponse
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class NoAuthSchemaGenerator(SchemaGenerator):
    """Schema generator that completely bypasses authentication."""
    
    def get_schema(self, request=None, public=False):
        """Generate schema without any authentication components."""
        schema = super().get_schema(request, public)
        # Remove security definitions and requirements
        if 'components' in schema and 'securitySchemes' in schema['components']:
            del schema['components']['securitySchemes']
        return schema


class SafeSpectacularAPIView(SpectacularAPIView):
    """
    Custom implementation that safely generates the schema without causing errors.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    generator_class = NoAuthSchemaGenerator
    
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Safely generate and return schema without authentication errors."""
        try:
            return super().get(request, *args, **kwargs)
        except TypeError:
            # If the standard view fails, fall back to our custom implementation
            generator = self.generator_class(
                urlconf=getattr(self, 'urlconf', None),
                api_version=getattr(self, 'api_version', None),
                patterns=getattr(self, 'patterns', None)
                # Removed problematic serve_permissions parameter
            )
            schema = generator.get_schema(request, public=True)
            renderer = OpenApiJsonRenderer()
            response = JsonResponse(schema)
            return response
