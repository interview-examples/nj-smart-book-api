"""
URL configuration for books_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

from books_api.views import api_schema, api_docs


def root_view(request):
    return HttpResponse(
        "Welcome to Smart Books API. Visit <a href='/api/v1/docs/'>API Documentation</a> for more information."
    )


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Root URL
    path("", root_view, name="root"),
    # API endpoints
    path("api/v1/", include("books.urls")),
]

# API documentation - simple custom implementation
urlpatterns += [
    path("api/v1/schema/", api_schema, name="schema"),
    path("api/v1/docs/", api_docs, name="swagger-ui"),
]
