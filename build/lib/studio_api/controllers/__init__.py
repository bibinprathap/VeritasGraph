"""Controllers for the studio API.

Mirrors the surrounding service convention: controllers are async, offload the
synchronous store calls onto a worker thread with ``asyncio.to_thread`` and
return ``JSONResponse`` envelopes shaped as ``{"message": ..., <payload>}``.
"""
