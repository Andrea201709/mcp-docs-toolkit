"""Keycloak document backend adapter."""

from mcp_docs_toolkit.adapters.keycloak.adapter import KeycloakBackendFactory
from mcp_docs_toolkit.adapters.registry import register_backend

register_backend(KeycloakBackendFactory())
