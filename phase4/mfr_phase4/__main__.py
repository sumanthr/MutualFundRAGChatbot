from __future__ import annotations

import uvicorn

from mfr_phase4.settings import API_HOST, API_PORT


def main() -> None:
    uvicorn.run(
        "mfr_phase4.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
