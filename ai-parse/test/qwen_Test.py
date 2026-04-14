from openai import OpenAI
import json

# ====================== 1. 大模型调用封装 ======================
class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url="http://127.0.0.1:8000/v1",
            api_key="test"
        )
        self.model_path = "qwen-7b"

    def chat(self, messages, temperature=0.3):
        """调用大模型，返回文本回答"""
        response = self.client.chat.completions.create(
            model=self.model_path,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

# ====================== 2. 短期记忆模块 ======================
class ShortTermMemory:
    def __init__(self, max_rounds=5):
        self.memory = []
        self.max_rounds = max_rounds  # 最大记忆轮数，防止过长

    def add(self, role, content):
        """添加记忆"""
        self.memory.append({"role": role, "content": content})
        # 限制记忆长度
        if len(self.memory) > self.max_rounds * 2:
            self.memory = self.memory[2:]

    def get_memory(self):
        """获取所有记忆"""
        return self.memory

    def clear(self):
        """清空记忆"""
        self.memory = []

# ====================== 3. 工具库（Agent可调用） ======================
class AgentTools:
    @staticmethod
    def calculate(expression):
        """简易计算器工具，处理数学计算"""
        try:
            # 安全计算简单数学表达式
            result = eval(expression, {"__builtins__": None}, {})
            return f"计算结果：{expression} = {result}"
        except Exception as e:
            return f"计算失败：{str(e)}"

    @staticmethod
    def get_tool_list():
        """获取工具描述，给大模型看"""
        return """
可用工具：
1. calculate：数学计算器
   参数：expression（数学表达式，如 "100+200*3"）
使用格式（必须严格JSON）：
{"tool":"calculate","params":{"expression":"计算式"}}
        """

# ====================== 4. 简易Agent核心 ======================
class SimpleAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.memory = ShortTermMemory()
        self.tools = AgentTools()

    def build_prompt(self, user_input):
        """构建Agent思考Prompt，包含记忆+工具说明"""
        system_prompt = f"""
你是一个智能助手Agent，具备工具调用能力。
规则：
1. 先判断问题是否需要工具，不需要则直接回答
2. 需要工具时，严格输出JSON格式调用指令，不要多余文字
3. 不需要工具则正常自然回答
4. 结合历史对话理解问题

{self.tools.get_tool_list()}
        """
        # 拼接系统提示+记忆+用户问题
        messages = [{"role": "system", "content": system_prompt}]
        messages += self.memory.get_memory()
        messages.append({"role": "user", "content": user_input})
        return messages

    def parse_tool_call(self, response):
        """解析模型是否调用工具"""
        try:
            # 尝试解析JSON工具调用
            tool_json = json.loads(response.strip())
            return tool_json
        except:
            # 不是工具调用，直接返回文本
            return None

    def run(self, user_input):
        """Agent执行主逻辑"""
        # 1. 构建Prompt
        messages = self.build_prompt(user_input)
        # 2. 调用大模型思考
        llm_response = self.llm.chat(messages)
        # 3. 解析是否调用工具
        tool_call = self.parse_tool_call(llm_response)
        
        if tool_call:
            print(f"模型调用工具：{tool_call}")
            # 执行工具
            tool_name = tool_call["tool"]
            params = tool_call["params"]
            if tool_name == "calculate":
                tool_result = self.tools.calculate(params["expression"])
            else:
                tool_result = "未知工具"
            
            # 工具结果再给模型整理回答
            final_prompt = messages + [
                {"role": "assistant", "content": llm_response},
                {"role": "user", "content": f"工具执行结果：{tool_result}，请整理成自然语言回答"}
            ]
            final_answer = self.llm.chat(final_prompt)
        else:
            # 无需工具，直接回答
            final_answer = llm_response

        # 4. 保存对话记忆
        self.memory.add("user", user_input)
        self.memory.add("assistant", final_answer)
        
        return final_answer

# ====================== 5. 交互主程序 ======================
if __name__ == "__main__":
    print("="*50)
    print("🤖 简易智能Agent系统已启动（基于Qwen2-7B）")
    print("输入 'exit' 退出，输入 'clear' 清空记忆")
    print("="*50)
    
    agent = SimpleAgent()
    
    while True:
        user_input = input("\n你：")
        if user_input.lower() == "exit":
            print("👋 Agent已退出")
            break
        if user_input.lower() == "clear":
            agent.memory.clear()
            print("🧹 记忆已清空")
            continue
        
        # Agent执行
        print("Agent思考中...")
        answer = agent.run(user_input)
        print(f"Agent：{answer}")