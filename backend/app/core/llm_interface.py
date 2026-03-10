import os
from typing import Optional
import httpx


class DummyLLM:
    def generate(self, prompt: str) -> str:
        # 先做一个可见的输出，方便你调试风格是否变化
        head = prompt.splitlines()[:12]
        return "【DummyLLM】我收到了如下 Prompt（前 12 行）:\n" + "\n".join(head)


class OllamaLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: int = 120,
        temperature: float = 0.3,
        num_predict: int = 512,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.num_predict = num_predict

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            return data.get("response", "").strip()
        except Exception as e:
            # 不让整个系统崩：把错误信息返回（你也可以选择 raise）
            return f"【Ollama call failed】{type(e).__name__}: {e}"


def get_llm():
    """
    按环境变量选择 LLM 后端：
      - LLM_BACKEND=dummy  -> DummyLLM
      - LLM_BACKEND=ollama -> OllamaLLM
    """
    backend = os.getenv("LLM_BACKEND", "dummy").lower().strip()

    if backend == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "mistral")
        timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
        num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))

        return OllamaLLM(
            base_url=base_url,
            model=model,
            timeout_s=timeout_s,
            temperature=temperature,
            num_predict=num_predict,
        )

    # 默认 dummy
    return DummyLLM()