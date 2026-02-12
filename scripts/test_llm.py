from __future__ import annotations

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
