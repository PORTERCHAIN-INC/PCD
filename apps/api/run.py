#!/usr/bin/env python3
"""Run Porterchain API with uvicorn."""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORTERCHAIN_API_PORT", "8001"))
    uvicorn.run(
        "porterchain_api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
