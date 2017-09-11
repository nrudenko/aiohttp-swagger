from collections import defaultdict

import yaml
from aiohttp import web
from aiohttp.hdrs import METH_ANY, METH_ALL


def _extract_swagger_docs(end_point_doc, method="get"):
    # Find Swagger start point in doc
    end_point_swagger_start = 0
    for i, doc_line in enumerate(end_point_doc):
        if "---" in doc_line:
            end_point_swagger_start = i + 1
            break

    # Build JSON YAML Obj
    try:
        end_point_swagger_doc = (
            yaml.load("\n".join(end_point_doc[end_point_swagger_start:]))
        )
    except yaml.YAMLError:
        end_point_swagger_doc = {
            "description": "⚠ Swagger document could not be loaded "
                           "from docstring ⚠",
            "tags": ["Invalid Swagger"]
        }
    return {method: end_point_swagger_doc}


def _build_doc_from_func_doc(route):
    out = {}
    if issubclass(route.handler, web.View) and route.method == METH_ANY:
        print(route.handler, route.handler)
        method_names = {
            attr for attr in dir(route.handler) if attr.upper() in METH_ALL
        }
        for method_name in method_names:
            method = getattr(route.handler, method_name)
            if method.__doc__ is not None and "---" in method.__doc__:
                end_point_doc = method.__doc__.splitlines()
                path = _extract_swagger_docs(end_point_doc, method=method_name)
                out.update(path)
    elif isinstance(route, web.AbstractRoute):
        method_name = route.method.lower()
        end_point_doc = route.handler.__doc__.splitlines()
        path = _extract_swagger_docs(end_point_doc, method=method_name)
        out.update(path)
    else:
        try:
            end_point_doc = route.handler.__doc__.splitlines()
        except AttributeError:
            return {}
        path = _extract_swagger_docs(end_point_doc)
        out.update(path)
    return out


def _build_paths_from_routes(routes):
    paths = defaultdict(dict)
    for route in routes:
        # If route has a external link to doc, we use it, not function doc
        if hasattr(route.handler, "swagger_file"):
            end_point_doc = _get_path_from_file(route)
        # Check if end-point has Swagger doc
        else:
            end_point_doc = _build_doc_from_func_doc(route)
        # there is doc available?
        if end_point_doc:
            url_info = route._resource.get_info()
            url = url_info.get("path", url_info.get("formatter"))

            paths[url].update(end_point_doc)
    return paths


def generate_swagger(
        app: web.Application,
        *,
        api_base_url: str = "/",
        description: str = "Swagger API definition",
        api_version: str = "1.0.0",
        title: str = "Swagger API",
        contact: str = "") -> dict:
    # Load base Swagger base dict
    swagger = {
        "swagger": "2.0",
        "info": {
            "description": description,
            "version": api_version,
            "title": title,
            "contact": contact
        },
        "basePath": api_base_url,
        "schemes": [
            "http",
            "https"
        ],
        "paths": _build_paths_from_routes(app.router.routes())}

    return swagger


def _get_path_from_file(route):
    try:
        end_point_doc = {
            route.method.lower(): {
                load_doc_from_yaml_file(route.swagger_file)
            }
        }
    except yaml.YAMLError:
        end_point_doc = {
            route.method.lower(): {
                "description": "⚠ Swagger document could not be "
                               "loaded from file ⚠",
                "tags": ["Invalid Swagger"]
            }
        }
    except FileNotFoundError:
        end_point_doc = {
            route.method.lower(): {
                "description":
                    "⚠ Swagger file not "
                    "found ({}) ⚠".format(route.handler.swagger_file),
                "tags": ["Invalid Swagger"]
            }
        }
    return end_point_doc


def load_doc_from_yaml_file(yaml_file_path: str):
    with open(yaml_file_path, "r") as f:
        swagger = yaml.load(f.read())
    return swagger


__all__ = (
    "generate_swagger",
    "load_doc_from_yaml_file"
)
