# sitecustomize.py
# Compatibility shim: restore huggingface_hub.cached_download if missing.
# This lets older code that expects cached_download continue to work.

import importlib
import logging

logger = logging.getLogger("sitecustomize")

try:
    hf = importlib.import_module("huggingface_hub")
except Exception:
    hf = None

if hf is not None and not hasattr(hf, "cached_download"):
    try:
        # Newer huggingface_hub exposes hf_hub_download; match signature loosely.
        from huggingface_hub import hf_hub_download

        def cached_download(*args, **kwargs):
            """
            Minimal wrapper around hf_hub_download to emulate cached_download.
            Note: arguments mapping is approximate but works for typical uses.
            """
            # hf_hub_download returns a local file path
            return hf_hub_download(*args, **kwargs)

        setattr(hf, "cached_download", cached_download)
        logger.info("Patched huggingface_hub.cached_download -> hf_hub_download")
    except Exception as e:
        logger.exception("Failed to patch huggingface_hub.cached_download: %s", e)
