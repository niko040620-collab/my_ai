import requests
import streamlit as st
from typing import Dict, Any
from datetime import datetime

@st.cache_data(ttl=300)  # 缓存5分钟
def get_balance(api_key: str) -> Dict[str, Any]:
    """获取账户余额"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(
            "https://api.deepseek.com/user/balance",
            headers=headers,
            timeout=(5, 10)  # 连接超时5秒，读取超时10秒
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("⏰ 请求超时，请检查网络后重试")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 网络连接失败，请检查网络或代理设置")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("❌ API Key 无效，请检查 .env 文件中的 DEEPSEEK_API_KEY")
        else:
            st.error(f"⚠️ HTTP 错误 {e.response.status_code}：{e}")
        return None
    except Exception as e:
        st.error(f"❌ 获取余额失败：{e}")
        return None