# Security and evidence boundary

This release contains no `.env` files, app credentials, private keys, access tokens, Shopify Admin API credentials, or local runtime settings.

The frozen competitor fixtures deliberately retain public page evidence and historical identifiers so their signed checksums can prove replay behaviour. Some sanitized HTML contains strings such as `token`, `password`, or Shopify app markup because those are part of the captured public pages; the acquisition records state that token-bearing responses were not retained. These fixtures are validation evidence, not credentials.

The locked documents also retain a historical workspace-relative path and one local course-path citation. Those strings are required by the unchanged evidence contracts and do not grant filesystem or service access. The package does not include the referenced course, the wider company vault, the gallery app, `node_modules`, or any source-extraction or Shopify authentication configuration.

