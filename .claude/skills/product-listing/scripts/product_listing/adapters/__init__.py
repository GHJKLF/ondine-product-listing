"""Read-only source evidence adapters."""

from .jsonld_dom import JsonLdDomAdapter
from .shopify_ajax import ShopifyAjaxAdapter
from .frozen_bundle import FrozenBundleAdapter

__all__ = ["FrozenBundleAdapter", "JsonLdDomAdapter", "ShopifyAjaxAdapter"]
