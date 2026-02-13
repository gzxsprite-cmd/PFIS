from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm import get_llm


if __name__ == "__main__":
    llm = get_llm()
    message = llm.chat(
        [
            {"role": "system", "content": "You are a concise financial assistant."},
            {"role": "user", "content": "请用一句话总结分散投资的重要性。"},
        ]
    )
    print(message)
