from openai import OpenAI
import os
import json
import sys
import io
from dotenv import load_dotenv

# 修复Windows控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# -----------1. 初始化DeepSeek API客户端-----------
load_dotenv()  # 加载环境变量
api_key = os.getenv("OPENAI_API_KEY")  # 从环境变量获取API密钥
base_url = os.getenv("OPENAI_BASE_URL")  # 从环境变量获取API基础URL
model = os.getenv("MODEL")  # 从环境变量获取模型名称

client = OpenAI(api_key=api_key, base_url=base_url)  # 初始化API客户端  

def prompt_sentiment(text):
    prompt = f"""
    你是专业的情感分析专家，请对以下用户评论进行情感分类，分类结果只能是「正面」「负面」「中性」中的一个，
    并给出1-2句话的分类理由，严格以JSON格式返回，格式如下：
    {{
        "sentiment": "情感类别",
        "reason": "分类理由"
    }}
    """
    return prompt

def prompt_summarize(text, max_length=200):
    prompt = f"""
    你是专业的文章总结专家，请将以下文章总结成不超过{max_length}字的摘要，
    保留核心观点、关键数据和结论，语言通顺易懂，避免冗余。
    
    文章内容：{text}
    """
    return prompt



# -----------2. 场景1：情感分析专家-----------
def sentiment_analysis(text):
    prompt = prompt_sentiment(text)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return response.choices[0].message.content

# -----------3. 场景2：文章总结-----------
def  summarize_article(article, max_length=200):
    prompt = prompt_summarize(article, max_length)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3, # 低温度保证摘要准确
    )
    return response.choices[0].message.content

# -----------4. 场景3：Function Call复杂业务逻辑-----------
# 模拟业务工具：天气查询函数（实际应用中可以是API调用）
def get_weather(city, data):
    # 模拟天气数据
    weather_data = {
        "北京": {"今天": "晴，15-28℃，东北风3级，适合出行"},
        "上海": {"今天": "多云转小雨，18-25℃，东南风4级，建议带伞"},
        "深圳": {"今天": "晴转多云，24-32℃，西南风2级，炎热注意防暑"},
        "广州": {"明天": "小雨转阴，22-30℃，东风3级，湿度较大"},
    }
    if city in weather_data and data in weather_data[city]:
        return f"{city}的{data}天气：{weather_data[city][data]}"
    return f"抱歉，暂时无法查询到{city}的{data}天气信息。"

def get_food(food_name):
    food_data = {
        "薯片": "薯片是一种非常受欢迎的零食，口感酥脆，味道香甜，非常适合在休闲时食用。",
        "巧克力": "巧克力是一种非常受欢迎的零食，口感细腻，味道甜美，非常适合在休闲时食用。",
        "饼干": "饼干是一种非常受欢迎的零食，口感酥脆，味道香甜，非常适合在休闲时食用。",
    }
    if food_name in food_data:
        return f"{food_name}的介绍：{food_data[food_name]}"
    return f"抱歉，暂时无法查询到{food_name}的介绍。"

def get_movie(movie_name):
    movie_data = {
        "流浪地球": "流浪地球是一部非常受欢迎的科幻电影，讲述了一个关于地球流浪的故事。",
        "复仇者联盟": "复仇者联盟是一部非常受欢迎的科幻电影，讲述了一个关于复仇者联盟的故事。",
        "变形金刚": "变形金刚是一部非常受欢迎的科幻电影，讲述了一个关于变形金刚的故事。",
    }
    if movie_name in movie_data:
        return f"{movie_name}的介绍：{movie_data[movie_name]}"
    return f"抱歉，暂时无法查询到{movie_name}的介绍。"


def function_call_example(user_input):
    """
    Function Call示例：用户输入查询天气的自然语言指令，模型解析指令并调用对应函数获取结果。
    : param user_input: 用户的自然语言指令，例如「请告诉我北京今天的天气」
    """
    # 1. 定义工具函数（Function Call的工具描述，严格遵循JSON Schema）
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "要查询天气的城市名称，例如「北京」「上海」"
                        },
                        "data": {
                            "type": "string",
                            "description": "要查询的天气数据类型，例如「今天」「明天」，默认是「今天」"
                        }
                    },
                    "required": ["city"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_food",
                "description": "查询某种零食或食物的介绍信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "food_name": {
                            "type": "string",
                            "description": "要查询的零食名称，例如「薯片」「巧克力」「饼干」"
                        }
                    },
                    "required": ["food_name"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_movie",
                "description": "查询电影的介绍信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "movie_name": {
                            "type": "string",
                            "description": "要查询的电影名称，例如「流浪地球」「复仇者联盟」"
                        }
                    },
                    "required": ["movie_name"],
                    "additionalProperties": False
                }
            }
        }
    ]

    # 2. 第一次调用，让大模型判断是否需要调用工具
    messages = [{"role": "user", "content": user_input}]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto", # 让模型自动判断是否需要调用工具
            temperature=0.1,
        )
    except Exception as e:
        return f"API调用失败: {str(e)}"

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls  # 模型调用的工具信息，如果模型没有调用工具则为None

    # 3. 如果模型调用了工具，执行工具函数并将结果反馈给模型
    if tool_calls:
        messages.append(response_message)  # 将模型的响应加入对话历史

        for tool_call in tool_calls:
            function_name = tool_call.function.name  # 获取模型调用的函数名称
            function_args = json.loads(tool_call.function.arguments)  # 获取模型调用的函数参数（JSON字符串，需要解析成字典）
            function_result = "工具调用成功，但未返回有效结果。"

            # 执行天气调用，执行对应函数
            if function_name == "get_weather":
                function_result = get_weather(
                    city=function_args.get("city"),
                    data=function_args.get("data", "今天")  # 默认查询「今天」的天气
                )
            elif function_name == "get_food":
                function_result = get_food(
                    food_name=function_args.get("food_name")
                )
            elif function_name == "get_movie":
                function_result = get_movie(
                    movie_name=function_args.get("movie_name")
                )

            # 将工具函数的执行结果反馈给模型，继续对话
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": function_result
            })
        # 4. 第二次调用，让模型根据工具函数的结果继续生成响应
        try:
            second_response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
            )
            return second_response.choices[0].message.content
        except Exception as e:
            return f"第二次API调用失败: {str(e)}"
    else:
        # 模型没有调用工具，直接返回模型的响应内容
        return response_message.content

# -----------5. 测试示例-----------
if __name__ == "__main__":
    # 场景1测试：情感分析
    print("="*50)
    # print("场景1：情感分析测试")
    # comments = [
    #     "这个产品太棒了，我非常喜欢！",
    #     "一般般吧，没有宣传的那么好。",
    #     "功能还可以，先继续用一段时间看看。"
    # ]
    # for comment in comments:
    #     sentiment_result = json.loads(sentiment_analysis(comment))
    #     print("用户评论：", comment)
    #     print("情感分析结果：", sentiment_result['sentiment'])
    #     print("分析理由：", sentiment_result['reason'])
    #     print("-" * 50)

    # # 场景2测试：文章总结
    # article = """
    # 人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。近年来，随着深度学习和大数据的发展，AI技术取得了显著进展，在图像识别、自然语言处理、自动驾驶等领域展现出强大的能力。AI不仅改变了我们的生活方式，还在医疗、金融、教育等行业带来了革命性的变革。然而，AI的发展也引发了关于隐私、安全和伦理的广泛讨论，需要我们在享受技术带来便利的同时，积极应对相关挑战。
    # """
    # summary_result = summarize_article(article, max_length=150)
    # print(f"原文长度：{len(article)} 字符")
    # print("文章总结结果：", summary_result)

    # 场景3测试：Function Call复杂业务逻辑
    user_query = "我想去买零食，有没有菠萝干"
    function_call_result = function_call_example(user_query)
    print("用户查询：", user_query)
    print("Function Call结果：", function_call_result)  


