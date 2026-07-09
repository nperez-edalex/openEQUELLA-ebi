"""EQUELLA client facade.

This is the single import point for API client classes used by EBI.

Transport selection:
- AUTO (default): try SOAP first, then fallback to REST when SOAP is blocked.
- SOAP: force legacy SOAP transport.
- REST: force REST transport.
"""

import os

from equellaclient41 import *
from equellaclient41 import TLEClient as _SoapTLEClient
from equellaclient_rest import TLEClient as _RestTLEClient


def _should_fallback_to_rest(exc):
    message = str(exc).lower()
    fallback_markers = [
        "forbidden",
        "http 403",
        "http error 403",
        "soapservice",
        "soapinterface",
        "no service was found",
    ]
    for marker in fallback_markers:
        if marker in message:
            return True
    return False


class _AutoFallbackTLEClient:
    """Proxy client that falls back to REST when SOAP is unavailable."""

    def __init__(
        self,
        owner,
        institutionUrl,
        username,
        password,
        proxy="",
        proxyusername="",
        proxypassword="",
        debug=False,
        sso=0,
    ):
        self._impl = None

        try:
            self._impl = _SoapTLEClient(
                owner,
                institutionUrl,
                username,
                password,
                proxy,
                proxyusername,
                proxypassword,
                debug,
                sso,
            )
            return
        except Exception as exc:
            if not _should_fallback_to_rest(exc):
                raise

            if owner and hasattr(owner, "echo"):
                owner.echo(
                    "SOAP API unavailable or blocked. Falling back to REST transport."
                )

        self._impl = _RestTLEClient(
            owner,
            institutionUrl,
            username,
            password,
            proxy,
            proxyusername,
            proxypassword,
            debug,
            sso,
        )

    def __getattr__(self, name):
        return getattr(self._impl, name)


_transport = os.environ.get("EBI_API_TRANSPORT", "auto").strip().lower()

if _transport == "rest":
    TLEClient = _RestTLEClient
elif _transport == "soap":
    TLEClient = _SoapTLEClient
else:
    TLEClient = _AutoFallbackTLEClient
