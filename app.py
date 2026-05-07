import streamlit as st
import json
import time
from openai import OpenAI
from datetime import datetime
import os
from dotenv import load_dotenv
import base64
from PIL import Image
import io
from usage_api import *
from streamlit.components.v1 import html

# 检查是否已通过验证
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password_input = st.text_input("请输入访问密码", type="password")
    if st.button("验证"):
        correct_password = st.secrets.get("APP_PASSWORD", "默认密码")
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密码错误，拒绝访问")
    st.stop()


def run_scroll_to_bottom():
    """改进版：寻找特定的底部锚点并滚动"""
    st.session_state.scroll_counter += 1
    
    # 删除了最后的 key= 参数
    # 将计数器放到了 HTML 的注释 中，文本改变同样会触发 iframe 刷新
    html(f"""
        <script>
            function forceScroll() {{
                const anchor = window.parent.document.getElementById('scroll-bottom-anchor');
                if (anchor) {{
                    anchor.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
                }}
            }}
            // 立即尝试
            forceScroll();
            // 延迟重试，确保 Streamlit 渲染完新增加的编辑框
            setTimeout(forceScroll, 300);
            setTimeout(forceScroll, 800);
        </script>
    """, height=0)
# 加载 .env 文件中的环境变量
load_dotenv()

# 读取 DeepSeek API Key
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        st.error("❌ 未找到 DeepSeek API Key，请在 .env 或 Streamlit Cloud Secrets 中设置")
        st.stop()

# 初始化 OpenAI 客户端（全局，后续直接使用）
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def build_current_session_data():
    """根据当前会话状态构建标准JSON数据（与保存格式完全一致）"""
    # 确定会话ID：若已存在则沿用，否则用当前时间戳
    if st.session_state.current_session_id:
        session_id = st.session_state.current_session_id
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    return {
        "id": session_id,
        "messages": st.session_state.current_messages,
        "system_prompt": st.session_state.system_prompt,
        "timestamp": datetime.now().isoformat(),
        "user_avatar": st.session_state.user_avatar,
        "assistant_avatar": st.session_state.assistant_avatar
    }


# ---------- 初始化所有 Session State ----------
def init_session_state():
    # 聊天记录格式: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    if "current_messages" not in st.session_state:
        st.session_state.current_messages = []
    # 会话存储目录
    if "sessions_dir" not in st.session_state:
        st.session_state.sessions_dir = "chat_sessions"
    # 当前激活的会话ID
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    # 所有的会话列表
    if "all_sessions" not in st.session_state:
        st.session_state.all_sessions = {}
    # 系统提示词
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = "你是一位乐于助人的中文助手，回答要条理清晰、温文尔雅、内容详实。"
    # AI 模型参数
    if "temperature" not in st.session_state:
        st.session_state.temperature = 1.0
    if "top_p" not in st.session_state:
        st.session_state.top_p = 1.0
    # 当前是否处于编辑消息的状态
    if "editing_index" not in st.session_state:
        st.session_state.editing_index = -1
    # 编辑框中的临时文本
    if "edit_text" not in st.session_state:
        st.session_state.edit_text = ""
    if "reasoning_effort" not in st.session_state:
        st.session_state.reasoning_effort = "medium"
    if "user_avatar" not in st.session_state:
        st.session_state.user_avatar = None   # 存储 base64 或 None
    if "assistant_avatar" not in st.session_state:
        st.session_state.assistant_avatar = None
    if "pending_ai_request" not in st.session_state:
        st.session_state.pending_ai_request = None
    if "custom_save_filename" not in st.session_state:
        st.session_state.custom_save_filename = ""
    if "scroll_to_bottom_needed" not in st.session_state:
        st.session_state.scroll_to_bottom_needed = False
    if "scroll_counter" not in st.session_state:
        st.session_state.scroll_counter = 0
    if "confirm_delete_sid" not in st.session_state:
        st.session_state.confirm_delete_sid = None
init_session_state()

# ---------- 图像格式转换 ----------
def image_to_base64(uploaded_file):
    """将上传的文件转为 base64 字符串，可用于 avatar 参数"""
    if uploaded_file is None:
        return None
    try:
        # 限制图片大小（可选：resize）
        img = Image.open(uploaded_file)
        # 限制最大尺寸为 200x200 防止 Base64 过大
        img.thumbnail((200, 200))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        st.error(f"头像处理失败：{e}")
        return None


# ---------- 辅助函数：加载所有会话 ----------
def _load_all_sessions():
    if os.path.exists(st.session_state.sessions_dir):
        sessions = {}
        for filename in os.listdir(st.session_state.sessions_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(st.session_state.sessions_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions[data["id"]] = data
        st.session_state.all_sessions = sessions
    else:
        st.session_state.all_sessions = {}

# ---------- 侧边栏：配置区域 ----------
with st.sidebar:
    st.header("配置与工具")

    with st.expander("高级参数调节"):
        # 模型选择
        st.session_state.model_name = st.selectbox(
            "模型选择",
            ["deepseek-v4-flash", "deepseek-v4-pro"],
            index=0,
        )
        
        # 深思模式
        st.session_state.thinking_mode = st.checkbox(
            "启用深思模式 (Chain of Thought)",
            value=st.session_state.get("thinking_mode", False),
            help="打开后，模型会展示内部推理过程。注意：开启后下方温度和Top P调节将无效。"
        )
        
        # 推理深度（仅对v4-pro + 思考模式生效）
        reasoning_options = ["low", "medium", "high"]
        is_pro = st.session_state.model_name == "deepseek-v4-pro"
        reasoning_disabled = not (is_pro and st.session_state.thinking_mode)
    
        reasoning_val = st.select_slider(
            "推理深度 (reasoning_effort)",
            options=reasoning_options,
            value=st.session_state.get("reasoning_effort", "medium"),
            disabled=reasoning_disabled,
                help="仅对 deepseek-v4-pro 且开启深思模式时有效。深度越大，推理越详细，耗时和成本略增。"
        )
        if not reasoning_disabled:
            st.session_state.reasoning_effort = reasoning_val
    
        # Temperature 和 Top P（思考模式下禁用）
        disabled_sliders = st.session_state.thinking_mode
        temperature = st.slider("Temperature", 0.0, 2.0, st.session_state.temperature, 0.1,
                                disabled=disabled_sliders, help="开启深思模式后无效")
        top_p = st.slider("Top P", 0.0, 1.0, st.session_state.top_p, 0.05,
                          disabled=disabled_sliders, help="开启深思模式后无效")
        if not disabled_sliders:
            st.session_state.temperature = temperature
            st.session_state.top_p = top_p


    # ---- 5. 更换系统提示词 ----
    with st.expander("更换系统提示词"):
        new_system_prompt = st.text_area("定义AI的性格/角色", value=st.session_state.system_prompt, height=150)
        if st.button("应用新提示词"):
            st.session_state.system_prompt = new_system_prompt
            st.success("系统提示词已更新！")
            st.rerun()

    # ---- 会话管理（全功能折叠面板）----
    with st.expander("会话管理", expanded=True):
        # 新建对话按钮
        if st.button("新建对话", use_container_width=True):
            st.session_state.current_messages = []
            st.session_state.current_session_id = None
            st.session_state.editing_index = -1
            st.session_state.user_avatar = None
            st.session_state.system_prompt = "你是一位乐于助人的中文助手，回答要条理清晰、温文尔雅、内容详实。"  # 重置为默认系统提示词
            st.session_state.assistant_avatar = None
            st.rerun()

        st.session_state.custom_save_filename = st.text_input(
            "自定义保存文件名（不含扩展名）",
            value=st.session_state.custom_save_filename,
            placeholder="留空则使用时间戳自动生成",
            key="save_filename_input"
        )

        # 保存当前对话到本地 JSON 文件
        if st.button("保存当前对话", use_container_width=True):
            if not st.session_state.current_messages:
                st.warning("没有内容可保存")
            else:
                if not os.path.exists(st.session_state.sessions_dir):
                    os.makedirs(st.session_state.sessions_dir)
            
                raw_name = st.session_state.custom_save_filename.strip()
                if raw_name:
                    import re
                    safe_name = re.sub(r'[\\/*?:"<>|]', "_", raw_name)
                    base_id = safe_name if safe_name else "session"
                else:
                    base_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
                final_id = base_id
                st.session_state.current_session_id = final_id
            
                session_data = {
                    "id": final_id,
                    "messages": st.session_state.current_messages,
                    "system_prompt": st.session_state.system_prompt,
                    "timestamp": datetime.now().isoformat(),
                    "user_avatar": st.session_state.user_avatar,
                    "assistant_avatar": st.session_state.assistant_avatar
                }
                file_path = os.path.join(st.session_state.sessions_dir, f"{final_id}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
            
                st.success(f"对话已保存至 {file_path}")
                _load_all_sessions()

        st.divider()   # 分割线：区分保存与导入导出

        # ----- 导入/导出子区域 -----
        st.subheader("导入/导出对话")

        # 导出按钮
        if st.button("导出当前对话为 JSON 文件", use_container_width=True, key="export_btn"):
            if not st.session_state.current_messages:
                st.warning("当前没有对话内容可导出")
            else:
                export_data = build_current_session_data()
                json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
                file_name = f"{export_data['id']}.json"
                st.download_button(
                    label="点击下载 JSON 文件",
                    data=json_str,
                    file_name=file_name,
                    mime="application/json",
                    key="real_download_btn"
                )

        # 上传 JSON 文件
        uploaded_json = st.file_uploader(
            "上传 JSON 对话文件",
            type=["json"],
            key="upload_session_json",
            help="请上传之前导出的 .json 文件（格式与云端保存一致）"
        )
        if uploaded_json is not None:
            try:
                uploaded_data = json.load(uploaded_json)
                required_keys = ["messages", "system_prompt", "id", "timestamp", "user_avatar", "assistant_avatar"]
                if not all(key in uploaded_data for key in required_keys):
                    st.error("文件格式不正确：缺少必要字段（messages, system_prompt, id, timestamp, user_avatar, assistant_avatar）")
                else:
                    st.info(f"已加载文件：{uploaded_json.name}\n会话 ID：{uploaded_data['id']}\n创建时间：{uploaded_data['timestamp']}")
                    if st.button("加载此对话并替换当前会话", use_container_width=True, key="load_uploaded_session"):
                        st.session_state.current_messages = uploaded_data["messages"]
                        st.session_state.current_session_id = uploaded_data["id"]
                        st.session_state.system_prompt = uploaded_data.get("system_prompt", st.session_state.system_prompt)
                        st.session_state.user_avatar = uploaded_data.get("user_avatar", None)
                        st.session_state.assistant_avatar = uploaded_data.get("assistant_avatar", None)
                        st.session_state.editing_index = -1
                        st.success(f"已成功加载对话：{uploaded_data['id']}")
                        st.rerun()
            except json.JSONDecodeError:
                st.error("文件不是合法的 JSON 格式")
            except Exception as e:
                st.error(f"读取文件失败：{e}")

        st.divider()   # 分割线：区分导入导出与云端会话管理

        # ----- 云端会话管理（加载已有会话）-----
        st.subheader("云端会话管理")
        _load_all_sessions()
        if st.session_state.all_sessions:
            session_options = {f"{sid} ({data.get('timestamp', '未知时间')})": sid for sid, data in st.session_state.all_sessions.items()}
            selected_label = st.selectbox("加载历史对话", list(session_options.keys()), key="load_session_select")
            selected_sid = session_options[selected_label]
            
            col_load, col_del = st.columns(2)
            with col_load:
                if st.button("加载选中对话", use_container_width=True):
                    file_path = os.path.join(st.session_state.sessions_dir, f"{selected_sid}.json")
                    with open(file_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                    st.session_state.current_messages = session_data["messages"]
                    st.session_state.current_session_id = session_data["id"]
                    st.session_state.system_prompt = session_data.get("system_prompt", st.session_state.system_prompt)
                    st.session_state.editing_index = -1
                    st.session_state.user_avatar = session_data.get("user_avatar", None)
                    st.session_state.assistant_avatar = session_data.get("assistant_avatar", None)
                    st.success(f"已加载对话：{selected_sid}")
                    st.rerun()
            
            with col_del:
                if st.button("删除选中对话", use_container_width=True):
                    st.session_state.confirm_delete_sid = selected_sid
                    st.rerun()
            
            # 删除确认处理
            if st.session_state.confirm_delete_sid is not None:
                sid_to_delete = st.session_state.confirm_delete_sid
                st.warning(f"确定要永久删除对话「{sid_to_delete}」吗？此操作不可恢复。")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("确认", key="confirm_delete_yes"):
                        file_path = os.path.join(st.session_state.sessions_dir, f"{sid_to_delete}.json")
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                st.success(f"已删除对话：{sid_to_delete}")
                                if st.session_state.current_session_id == sid_to_delete:
                                    st.session_state.current_messages = []
                                    st.session_state.current_session_id = None
                                    st.session_state.user_avatar = None
                                    st.session_state.assistant_avatar = None
                                _load_all_sessions()
                                st.session_state.confirm_delete_sid = None
                                st.rerun()
                            else:
                                st.error("文件不存在，可能已被删除")
                                st.session_state.confirm_delete_sid = None
                                st.rerun()
                        except Exception as e:
                            st.error(f"删除失败：{e}")
                            st.session_state.confirm_delete_sid = None
                            st.rerun()
                with col_cancel:
                    if st.button("取消", key="confirm_delete_no"):
                        st.session_state.confirm_delete_sid = None
                        st.rerun()
        else:
            st.info("暂无云端保存的对话，请先保存当前对话。")
    
    # ---- 自定义头像 ----
    with st.expander("自定义头像", expanded=False):
        # 用户头像上传
        user_avatar_file = st.file_uploader("上传用户头像", type=["png", "jpg", "jpeg", "gif"], key="user_avatar_uploader")
        if not hasattr(st.session_state, '_last_user_avatar_id'):
            st.session_state._last_user_avatar_id = None
        if user_avatar_file is not None:
            file_id = f"{user_avatar_file.name}_{user_avatar_file.size}"
            if file_id != st.session_state._last_user_avatar_id:
                st.session_state._last_user_avatar_id = file_id
                new_avatar = image_to_base64(user_avatar_file)
                if new_avatar:
                    st.session_state.user_avatar = new_avatar
                    st.success("用户头像已更新")
                    st.rerun()
        
        # 助手头像上传
        assistant_avatar_file = st.file_uploader("上传助手头像", type=["png", "jpg", "jpeg", "gif"], key="assistant_avatar_uploader")
        if not hasattr(st.session_state, '_last_assistant_avatar_id'):
            st.session_state._last_assistant_avatar_id = None
        if assistant_avatar_file is not None:
            file_id = f"{assistant_avatar_file.name}_{assistant_avatar_file.size}"
            if file_id != st.session_state._last_assistant_avatar_id:
                st.session_state._last_assistant_avatar_id = file_id
                new_avatar = image_to_base64(assistant_avatar_file)
                if new_avatar:
                    st.session_state.assistant_avatar = new_avatar
                    st.success("助手头像已更新")
                    st.rerun()
        
        # 显示当前头像预览
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**当前用户头像**")
            if st.session_state.user_avatar:
                st.image(st.session_state.user_avatar, width=80)
            else:
                st.info("未自定义")
        with col2:
            st.markdown("**当前助手头像**")
            if st.session_state.assistant_avatar:
                st.image(st.session_state.assistant_avatar, width=80)
            else:
                st.info("未自定义")
    # ---- 余额监控（独立区域，亦可放入 expander）----
    st.divider()  # 可选的分隔线
    with st.expander("余额监控", expanded=False):
        # 第一行：余额数值与刷新按钮
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**账户余额**")
        with col2:
            if st.button("刷新", key="refresh_balance_sidebar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        # 第二行：余额具体数值（使用缓存避免频繁请求）
        with st.spinner("加载中..."):
            # 这里可以使用 st.cache_data 缓存余额数据，避免每次刷新页面都调用 API
            @st.cache_data(ttl=60)  # 缓存 60 秒
            def get_cached_balance():
                return get_balance(DEEPSEEK_API_KEY)
            
            balance_data = get_cached_balance()
            if balance_data and balance_data.get("is_available"):
                balance_info = balance_data["balance_infos"][0]
                balance_value = f"¥{balance_info.get('total_balance', '0.00')}"
                st.markdown(
                    f"<p style='font-size:28px; font-weight:bold; margin:0;'>{balance_value}</p>",
                    unsafe_allow_html=True
                )
                st.caption("总额为充值金额与赠送金额之和")
            else:
                st.warning("无法获取余额，请检查 API Key")


# ---------- 主界面：聊天区域 ----------
st.title("DeepSeek 智能聊天室")
st.caption(f"当前系统提示词：{st.session_state.system_prompt[:50]}...")
st.markdown("""
<style>
    /* 1. 强制隐藏标记并使其不占位 */
    .user-marker {
        display: none !important;
        position: absolute !important; /* 彻底脱离文档流，不占用任何高度 */
    }

    /* 2. 消除气泡内部第一个元素的上边距 */
    /* Streamlit 渲染 Markdown 会产生 <p> 标签，我们需要去掉第一个 p 的 margin-top */
    div[data-testid="stChatMessage"]:has(.user-marker) div[data-testid="stChatMessageContent"] p:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 3. 用户消息整体容器 */
    div[data-testid="stChatMessage"]:has(.user-marker) {
        flex-direction: row-reverse !important;
        background-color: transparent !important;
        align-items: flex-start !important;
        padding: 0 !important;
    }

    /* 4. 用户气泡背景与对齐 */
    div[data-testid="stChatMessage"]:has(.user-marker) div[data-testid="stChatMessageContent"] {
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        padding: 10px 16px !important;
        border-radius: 12px 2px 12px 12px !important;
        margin-right: 12px !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;

        /* --- 核心修改部分 --- */
        display: block !important;       /* 恢复为块级，方便控制内部对齐 */
        width: fit-content !important;    /* 宽度根据内容自动缩拢 */
        max-width: 80% !important;        /* 限制最大宽度，防止长文本溢出 */
        margin-left: auto !important;     /* 关键：配合 fit-content 将整个气泡推向右侧 */
        text-align: left !important;      /* 气泡内部文字恢复左对齐，符合阅读习惯 */
    }

    div[data-testid="stChatMessage"]:has(.user-marker) div[data-testid="stChatMessageContent"] p {
        text-align: right !important;
    }

    /* 5. 调整头像位置 (根据你的截图微调) */
    div[data-testid="stChatMessage"]:has(.user-marker) div[data-testid="stChatMessageAvatarContainer"] {
        transform: translateY(5px) !important; 
    }

    /* 6. 调整编辑按钮位置 (根据你的截图微调) */
    .edit-btn-container {
        display: flex;
        justify-content: center;

    }
    div[data-testid="stChatMessage"]:has(.user-marker) p:has(span.user-marker) {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 0 !important;
        font-size: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stChatMessage"]:has(.user-marker) div[data-testid="stChatMessageContent"] .stVerticalBlock {
        gap: 0 !important;
    }
    div[data-testid="stChatMessage"] {
        margin: 0 0 0px 0 !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex;
        align-items: stretch !important;
    }
    div[data-testid="stHorizontalBlock"] > div:first-child {
        display: flex;
        flex-direction: column;
        justify-content: center;
        /* 移除可能影响高度的 padding/margin */
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stHorizontalBlock"] > div:first-child .stButton {
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.current_messages):
        if msg["role"] == "user" and st.session_state.editing_index != i:
            # 这里的比例可以根据你的头像大小微调，[0.1, 0.9] 通常效果较好
            cols = st.columns([0.1, 0.9], gap="small")
            
            with cols[0]: # 左侧编辑按钮
                is_editing_now = st.session_state.editing_index != -1

                if st.button("✏️", key=f"edit_btn_{i}", help="编辑消息", disabled=is_editing_now):
                    st.session_state.editing_index = i
                    st.session_state.edit_text = msg["content"]
                    run_scroll_to_bottom() # <--- 这里确保调用
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            with cols[1]: # 右侧：消息与头像
                with st.chat_message("user", avatar=st.session_state.user_avatar):
                    st.markdown('<span class="user-marker"></span>', unsafe_allow_html=True)
                    st.markdown(msg["content"])
                    
        elif msg["role"] == "assistant":
            # 助手消息保持原样，Streamlit 默认就是头像与第一行对齐的
            with st.chat_message("assistant", avatar=st.session_state.assistant_avatar):
                
                if "usage" in msg:
                    # 显示本次回复消耗的 Token 数
                    usage = msg["usage"]
                    st.caption(f"⚡ 本次消耗：输入 {usage['input_tokens']} / 输出 {usage['output_tokens']} Tokens")
                # 1. 先显示推理过程（折叠块，默认折叠）
                if "reasoning" in msg and msg["reasoning"]:
                    with st.expander("思考过程", expanded = True):
                        st.markdown(
                            f"<div style='color: #A1A1AA;'>{msg['reasoning']}</div>", 
                            unsafe_allow_html=True
                        )
                # 2. 再显示最终回答
                st.markdown(msg["content"])

# ---------- 辅助函数：生成 AI 回复 ----------
def _generate_ai_response():
    user_input = st.session_state.pending_ai_request
    if not user_input:
        return
    st.session_state.pending_ai_request = None

    # 构建 API 消息列表
    api_messages = [
        {"role": "system", "content": st.session_state.system_prompt}
    ] + st.session_state.current_messages

    # API 参数
    api_params = {
        "model": st.session_state.model_name,
        "messages": api_messages,
        "temperature": st.session_state.temperature,
        "top_p": st.session_state.top_p,
        "stream": True,  # 保持流式
    }

    # 深思模式参数
    if st.session_state.thinking_mode:
        extra_body = {"thinking": {"type": "enabled"}}
        if st.session_state.model_name == "deepseek-v4-pro":
            extra_body["reasoning_effort"] = st.session_state.reasoning_effort
        api_params["extra_body"] = extra_body

    # 在聊天区域创建一个助手消息容器
    with st.chat_message("assistant", avatar=st.session_state.assistant_avatar):
        # 推理过程 expander 和最终回复占位符
        with st.expander("思考过程", expanded=False):
            reasoning_placeholder = st.empty()
        content_placeholder = st.empty()

        reasoning_text = ""
        content_text = ""
        final_usage = None  # 用于存储最后一个 chunk 中的 usage

        try:
            response = client.chat.completions.create(**api_params)
            for chunk in response:
                delta = chunk.choices[0].delta

                # 推理内容
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_text += delta.reasoning_content
                    reasoning_placeholder.markdown(
    f"<div style='color: #A1A1AA;'>{reasoning_text}</div>", 
                        unsafe_allow_html=True
                    )

                # 最终回复内容
                if delta.content:
                    content_text += delta.content
                    content_placeholder.markdown(content_text)

                # 检查是否有 usage 字段（通常在最后一个 chunk 中）
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    final_usage = chunk.usage

            # 如果流式中没有 usage，可以尝试从 response 中获取（但 response 已消费完毕）
            # 此时 final_usage 应该已被赋值
            if final_usage is None:
                # 有可能流式不返回，则置空
                st.warning("未获取到本次调用的用量信息")
                usage_dict = None
            else:
                usage_dict = {
                    "input_tokens": final_usage.prompt_tokens,
                    "output_tokens": final_usage.completion_tokens,
                    "total_tokens": final_usage.total_tokens
                }

            # 保存消息
            assistant_msg = {"role": "assistant", "content": content_text}
            if reasoning_text:
                assistant_msg["reasoning"] = reasoning_text
            if usage_dict:
                assistant_msg["usage"] = usage_dict
            st.session_state.current_messages.append(assistant_msg)

        except Exception as e:
            error_msg = f"API 调用失败：{e}"
            content_placeholder.markdown(error_msg)
            st.session_state.current_messages.append({"role": "assistant", "content": error_msg})

    st.rerun()
# 如果有待处理的 AI 请求，立即生成回复
if st.session_state.pending_ai_request:
    _generate_ai_response()
# ---------- 底部的聊天输入框 ----------
# 根据是否处于编辑模式，显示不同的输入组件
if st.session_state.editing_index == -1:
    # 正常模式：显示可用的聊天输入框
    if user_input := st.chat_input("输入你的问题..."):
        st.session_state.current_messages.append({"role": "user", "content": user_input})
        st.session_state.pending_ai_request = user_input
        # 重点是：在正常消息发送后，也需要滚动到底部
        run_scroll_to_bottom()
        st.rerun()
else:
    # 编辑模式：显示禁用的输入框，提示用户先完成编辑
    st.text_area(
        label="",
        value="当前正在编辑消息，请先点击「确认重新发送」或「取消编辑」",
        disabled=True,
        height=40,
        label_visibility="collapsed",
        key="disabled_input_during_edit"
    )
    st.caption("💡 完成编辑后，底部输入框将恢复可用")

# 编辑模式处理：显示一个特殊的输入框用于修改消息
if st.session_state.editing_index != -1:
    original_msg = st.session_state.current_messages[st.session_state.editing_index]
    with st.chat_message("user", avatar=st.session_state.user_avatar):
        st.markdown('<span class="user-marker"></span>', unsafe_allow_html=True)
        edited_text = st.text_area("编辑你的消息后，点击下方按钮重新发送",
                                   value=st.session_state.edit_text,
                                   key="edit_text_area",
                                   height=100)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重新发送", key="confirm_edit", use_container_width=True):
                st.session_state.current_messages = st.session_state.current_messages[:st.session_state.editing_index]
                edited_text = st.session_state.edit_text
                st.session_state.current_messages.append({"role": "user", "content": edited_text})
                st.session_state.pending_ai_request = edited_text
                st.session_state.editing_index = -1
                st.session_state.edit_text = ""
                run_scroll_to_bottom()
                st.rerun()
        with col2:
            if st.button("取消编辑", key="cancel_edit", use_container_width=True):
                st.session_state.editing_index = -1
                st.session_state.edit_text = ""
                run_scroll_to_bottom()
                st.rerun()

    # ✅ 点击编辑按钮后，显示编辑界面时滚动到底部（使用改进后的函数）
    run_scroll_to_bottom()
# ---------- 整个脚本的最底部 ----------
st.markdown("<div id='scroll-bottom-anchor'></div>", unsafe_allow_html=True)
