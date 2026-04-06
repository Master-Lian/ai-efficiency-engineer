from openai import OpenAI, APIError, AuthenticationError, RateLimitError, APIConnectionError
from config import API_KEY,  BASE_URL, MODEL, TEMPERATURE
from utils.log_util import logger

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60)

def validate_api_key():
    if not API_KEY or len(API_KEY) < 10:  # 简单检查API_KEY长度
        logger.error("❌ API Key 为空或格式错误！")
        raise False

    try:
        client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[{"role": "system", "content": "测试API Key有效性"}],
        )
        logger.info("✅ API Key 验证成功！")
        return True

    except AuthenticationError:
        logger.error("❌ API Key 无效！（错误码：401）")
        logger.error("👉 解决办法：检查 .env 中的密钥是否正确，重新生成新的 API Key")
        return False

    except RateLimitError:
        logger.error("❌ API 额度不足/调用超限！（错误码：429）")
        logger.error("👉 解决办法：充值额度、提升配额，或更换密钥")
        return False

    except APIConnectionError:
        logger.error("❌ 网络连接失败！无法连接 OpenAI 服务")
        logger.error("👉 解决办法：检查网络、代理设置")
        return False

    except APIError as e:
        logger.error(f"❌ OpenAI 服务异常：{str(e)}")
        return False

    except Exception as e:
        logger.error(f"❌ 未知错误：{str(e)}")
        return False
    

def ai_call(prompt: str, content: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI调用失败: {e}")
        return f"处理异常: {e}"