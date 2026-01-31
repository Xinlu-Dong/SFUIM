class DummyLLM:
    def generate(self, prompt: str) -> str:
        # 先做一个可见的输出，方便你调试风格是否变化
        head = prompt.splitlines()[:12]
        return "【DummyLLM】我收到了如下 Prompt（前 12 行）:\n" + "\n".join(head)
