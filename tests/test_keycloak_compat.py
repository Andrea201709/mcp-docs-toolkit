"""Compatibility tests for legacy Keycloak module shims."""

from __future__ import annotations


def test_top_level_keycloak_modules_reexport_internal_implementations():
    from mcp_docs_toolkit import auth, client, config, mock_transport
    from mcp_docs_toolkit.adapters.keycloak import _auth, _client, _config_compat, _mock_transport

    assert auth.request_access_token is _auth.request_access_token
    assert client.DocumentApiClient is _client.DocumentApiClient
    assert config.Settings is _config_compat.Settings
    assert config.load_settings is _config_compat.load_settings
    assert mock_transport.mock_opener is _mock_transport.mock_opener
    assert mock_transport.mock_settings is _mock_transport.mock_settings
