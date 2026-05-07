# DeepSeek 智能聊天室

基于 Streamlit 和 DeepSeek API 构建的智能对话应用，支持多会话管理、模型参数调节、深思模式、头像自定义及余额监控等功能。

## 项目简介

本项目是一个功能完善的 DeepSeek API 聊天客户端，提供友好的 Web 界面，允许用户与 DeepSeek 大语言模型进行交互。主要面向需要管理多个对话、调节模型参数、保存和加载历史对话的开发者和终端用户。

## 主要功能

- 多会话管理：新建、保存、加载、删除对话，支持自定义文件名导出/导入 JSON 格式会话文件。
- 模型选择：支持 deepseek-v4-flash 和 deepseek-v4-pro 模型。
- 深思模式：开启后模型展示内部推理过程（Chain of Thought），对 deepseek-v4-pro 可额外调节推理深度（low/medium/high）。
- 参数调节：可分别调节 Temperature 和 Top P（深思模式下自动禁用）。
- 系统提示词：自定义 AI 的角色和性格，随时应用新提示词。
- 消息编辑：支持编辑已发送的用户消息，重新生成 AI 回复。
- 头像自定义：为用户和助手分别上传图片作为头像。
- 余额监控：通过 DeepSeek API 查询账户余额，支持缓存避免频繁请求。
- 响应信息显示：展示每次 AI 回复的 Token 消耗量（输入/输出）。
- 访问密码保护：通过 Streamlit Secrets 配置访问密码，限制未授权用户。

## 技术栈

- Python 3.8+
- Streamlit
- OpenAI Python SDK（兼容 DeepSeek API）
- Requests
- Pillow（头像图片处理）
- python-dotenv（环境变量管理）

## 安装与部署

### 本地运行

1. 克隆代码仓库

```bash
git clone <repository-url>
cd <project-directory>
```

2. 安装依赖

```bash
pip install streamlit openai requests pillow python-dotenv
```

3. 配置 API Key

在项目根目录创建 `.env` 文件，添加以下内容：

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

或者在 Streamlit 运行时通过 secrets 配置（见下文）。

4. 启动应用

```bash
streamlit run app.py
```

### 部署到 Streamlit Cloud

1. 将代码推送到 GitHub 仓库。
2. 在 [Streamlit Cloud](https://streamlit.io/cloud) 中连接该仓库。
3. 在应用的 Secrets 配置中添加以下键值对：

   - `DEEPSEEK_API_KEY`：你的 DeepSeek API 密钥
   - `APP_PASSWORD`（可选）：访问密码，用于保护应用

4. 部署后即可通过生成的 URL 访问。

## 配置说明

### 环境变量 / Secrets

| 变量名 | 说明 | 示例 |
|--------|------|------|
| DEEPSEEK_API_KEY | DeepSeek API 密钥 | `sk-xxxxxxxxxxxxxxxx` |
| APP_PASSWORD | 访问密码（可选），若不设置则默认为“默认密码” | `mysecret123` |

### 文件存储

- 保存的会话文件默认存储在 `chat_sessions/` 目录下，每个会话为一个 JSON 文件，文件名格式为 `<会话ID>.json`。
- 会话 ID 可以是自定义文件名或时间戳（`YYYYMMDD_HHMMSS`）。

### 头像上传

- 支持 PNG、JPG、JPEG、GIF 格式，上传后自动缩放到 200x200 像素以内并转为 Base64 存储。
- 头像数据保存在会话 JSON 文件中，导出/导入时会一同保留。

## 使用指南

1. **启动应用**：访问应用 URL（本地为 `http://localhost:8501`）。
2. **输入密码**：若配置了访问密码，首次进入需验证。
3. **开始对话**：在底部聊天输入框输入问题，按回车发送。
4. **调节模型参数**：在左侧边栏展开“高级参数调节”，选择模型、开启深思模式、调整推理深度、Temperature、Top P。
5. **修改系统提示词**：左侧边栏“更换系统提示词”区域，编辑后点击“应用新提示词”。
6. **管理会话**：
   - 新建对话：点击“新建对话”。
   - 保存对话：输入自定义文件名（可选），点击“保存当前对话”。
   - 导出对话：点击“导出当前对话为 JSON 文件”，然后点击下载按钮。
   - 导入对话：上传 JSON 文件，确认后点击“加载此对话并替换当前会话”。
   - 加载历史对话：在“云端会话管理”下拉框中选择一个会话，点击“加载选中对话”。
   - 删除会话：选中后点击“删除选中对话”，并确认。
7. **编辑消息**：鼠标悬停在用户消息左侧会出现编辑按钮（铅笔图标），点击后可修改消息内容并重新发送，AI 将基于编辑后的消息重新生成回复。
8. **自定义头像**：左侧边栏“自定义头像”区域上传用户或助手的头像图片。
9. **查看余额**：左侧边栏“余额监控”区域显示账户余额，可手动刷新。

## 重要说明

- 深思模式开启后，模型会返回 `reasoning_content` 字段，本应用将其显示在可折叠的“思考过程”区域内。
- 编辑消息时，原消息及其之后的所有消息将被删除，只保留编辑后的消息并重新请求 AI。
- 会话保存时，会一同保存当前系统提示词、头像配置和时间戳。
- 应用使用 Streamlit 的缓存机制减少对余额 API 的无效请求（缓存 60 秒）。

## 常见问题

**Q: 提示“未找到 DeepSeek API Key”怎么办？**  
A: 请检查是否在 `.env` 文件或 Streamlit Secrets 中正确设置了 `DEEPSEEK_API_KEY`。

**Q: 余额查询失败怎么办？**  
A: 确保 API Key 有效且网络可以访问 `https://api.deepseek.com`。如果使用代理，需在环境变量中设置 `HTTP_PROXY`/`HTTPS_PROXY`。

**Q: 深思模式下调节 Temperature 和 Top P 无效？**  
A: 这是设计行为：开启深思模式后，模型将使用固定的采样参数，Temperature 和 Top P 滑块会自动禁用。

**Q: 编辑消息后滚动不到底部？**  
A: 应用已内置滚动脚本，会在编辑界面渲染后自动滚动到底部。若仍有问题，可尝试手动滚动。

## 许可证

本项目的许可证信息请查阅仓库中的 LICENSE 文件。

## 致谢

- [DeepSeek](https://deepseek.com/) 提供大语言模型 API
- [Streamlit](https://streamlit.io/) 提供 Web 应用框架
