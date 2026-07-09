"""EQUELLA client facade.

This is the single import point for API client classes used by EBI.
EBI now uses REST transport only.
"""

from equellaclient41 import XPath
from equellaclient_rest import NewItemClient, PropBagEx, TLEClient

__all__ = ["TLEClient", "NewItemClient", "PropBagEx", "XPath"]
