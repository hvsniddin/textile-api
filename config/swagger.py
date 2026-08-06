import re

from django.http import HttpResponse, JsonResponse
from django.urls import URLPattern, URLResolver, get_resolver


HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def swagger_ui(request):
    return HttpResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Textile API Swagger</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body { margin: 0; background: #f6f8fa; }
    .swagger-ui .topbar { display: none; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/swagger.json",
      dom_id: "#swagger-ui",
      deepLinking: true,
      persistAuthorization: true,
      displayRequestDuration: true,
    });
  </script>
</body>
</html>
        """,
        content_type="text/html",
    )


def openapi_schema(request):
    return JsonResponse(_build_openapi_schema(request))


def _build_openapi_schema(request):
    paths = {}
    for route, callback in _iter_url_patterns(get_resolver().url_patterns):
        if _should_skip_route(route):
            continue

        openapi_path = _to_openapi_path(route)
        methods = _get_methods(callback)
        if not methods:
            continue

        for method, action in methods.items():
            paths.setdefault(openapi_path, {})[method] = _build_operation(
                request=request,
                method=method,
                path=openapi_path,
                callback=callback,
                action=action,
            )

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Textile API",
            "version": "1.0.0",
            "description": "API endpoints for the Textile application.",
        },
        "servers": [
            {
                "url": request.build_absolute_uri("/").rstrip("/"),
            }
        ],
        "paths": dict(sorted(paths.items())),
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    }


def _iter_url_patterns(patterns, prefix=""):
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from _iter_url_patterns(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern):
            yield route, pattern.callback


def _should_skip_route(route):
    return (
        not route
        or route.startswith("admin/")
        or route.startswith("swagger")
        or route.startswith("__debug__")
        or "format" in route
    )


def _to_openapi_path(route):
    route = route.replace("^", "").replace("$", "")
    route = re.sub(r"\(\?P<([^>]+)>[^)]+\)", r"{\1}", route)
    route = re.sub(r"<(?:[^:>/]+:)?([^>/]+)>", r"{\1}", route)
    route = re.sub(r"\.\?/?$", "", route)
    route = route.strip("/")
    return f"/{route}/" if route else "/"


def _get_methods(callback):
    if hasattr(callback, "actions"):
        return {
            method: action
            for method, action in callback.actions.items()
            if method in HTTP_METHODS
        }

    view_class = getattr(callback, "view_class", None)
    if not view_class:
        return {}

    methods = {}
    for method in getattr(view_class, "http_method_names", []):
        if method not in HTTP_METHODS:
            continue
        handler = getattr(view_class, method, None)
        if handler is not None:
            methods[method] = method
    return methods


def _build_operation(request, method, path, callback, action):
    view_class = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    view_name = view_class.__name__ if view_class else "API"
    operation_id = _operation_id(method, path, action)
    parameters = _path_parameters(path)
    operation = {
        "operationId": operation_id,
        "summary": _summary(method, action, view_name),
        "tags": [_tag_for_path(path)],
        "parameters": parameters,
        "responses": _responses(method),
    }

    if _requires_auth(path):
        operation["security"] = [{"BearerAuth": []}]
    else:
        operation["security"] = []

    if method in ("post", "put", "patch"):
        operation["requestBody"] = {
            "required": method in ("post", "put"),
            "content": {
                "application/json": {
                    "schema": {"type": "object"},
                }
            },
        }

    return operation


def _operation_id(method, path, action):
    path_name = re.sub(r"[^a-zA-Z0-9]+", "_", path.strip("/")).strip("_")
    return f"{method}_{path_name or 'root'}_{action}"


def _summary(method, action, view_name):
    readable_action = str(action).replace("_", " ")
    return f"{method.upper()} {readable_action} ({view_name})"


def _tag_for_path(path):
    parts = [part for part in path.strip("/").split("/") if part and not part.startswith("{")]
    if len(parts) >= 3 and parts[0] == "api" and parts[1].startswith("v"):
        return parts[2]
    return parts[0] if parts else "api"


def _path_parameters(path):
    return [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }
        for name in re.findall(r"{([^}]+)}", path)
    ]


def _responses(method):
    success_status = "201" if method == "post" else "204" if method == "delete" else "200"
    responses = {
        success_status: {
            "description": "Successful response",
        },
        "400": {
            "description": "Bad request",
        },
        "401": {
            "description": "Authentication credentials were not provided or are invalid.",
        },
    }
    if method in ("get", "put", "patch", "delete"):
        responses["404"] = {
            "description": "Not found",
        }
    return responses


def _requires_auth(path):
    public_paths = {
        "/auth/login/",
        "/auth/refresh/",
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
    }
    return path not in public_paths
