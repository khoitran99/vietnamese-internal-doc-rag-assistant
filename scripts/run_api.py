from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FastAPI server")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    os.environ["APP_CONFIG_PATH"] = args.config
    uvicorn.run("src.api.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
