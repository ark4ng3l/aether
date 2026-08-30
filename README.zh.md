<div align="center">

# 🌐 AETHER v4.0: 认知级自主网络威胁情报作战系统
**分层多智能体系统 • 多模态感知 • 自主认知修复 • GraphRAG 知识融合**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-38bdf8?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-v4.0-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Uncensored_AI-8b5cf6?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![Tests](https://img.shields.io/badge/Tests-143%20Passed%20(100%25)-10b981?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-38bdf8?style=for-the-badge)](LICENSE)

<br/>

**🌍 语言选择 / Languages / زبان‌ها / Языки:**  
[English](README.md) • [فارسی (Persian)](README.fa.md) • [Русский (Russian)](README.ru.md) • [中文 (Chinese)](README.zh.md)

</div>

---

## 🌟 核心特性与架构

**AETHER v4.0** 是一套专为威胁情报分析师打造的企业级自主开源网络情报（OSINT）与多模态认知推理平台。系统依托 **Ollama 完全在本地运行**，无需第三方云端 API，提供极致的操作安全（OPSEC）与数据隐私保障。

### 核心功能模块：
1. **分层多智能体系统 (Commander-Specialist-Critic)**：
   - 指挥官智能体 (`CommanderAgent`) 基于思维树 (Tree-of-Thought) 进行任务拆解与调度。
   - 专家智能体：网络情报 (`NetworkSpecialist`)、图像取证 (`VisionSpecialist`)、音频听觉 (`AudioSpecialist`)、动态工具合成 (`ToolmakerSpecialist`)。
   - 红队对抗批评者 (`RedTeamCritic`) 过滤幻觉与误报。
2. **认知级自主修复引擎 (Self-Healing Engine)**：
   - 根本原因分析 (RCA) 智能归类故障。
   - 参数动态转换与规范化 (Transmutation)。
   - 防御壁垒（WAF、429 速率限制）下自动切换至被动镜像资源。
   - 情景故障记忆库 (Episodic Memory) 沉淀修复模式。
3. **双层防护执行沙箱 (AST & Subprocess Sandbox)**：
   - AST 静态语法树拦截危险模块与内置函数。
   - 独立子进程配合资源配额（256MB 内存，10s CPU）与超时控制。
4. **多语言全功能界面 (i18n)**：
   - 原生支持中文、波斯语（含完整 RTL 与字体优化）、英语及俄语。

---

## ⚡ 快速开始

```bash
git clone https://github.com/ark4ng3l/aether.git
cd aether
pip install -r requirements.txt
python run.py
```

终端将打印带有会话安全令牌的访问链接：
`http://127.0.0.1:8000/#token=<SESSION_TOKEN>`
