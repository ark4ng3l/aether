<div align="center">

# 🌐 AETHER v4.0: The Autonomous Cyber-Intelligence Operator
**Hierarchical Multi-Agent System • Multimodal Perception • Cognitive Self-Healing • GraphRAG Fusion**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-38bdf8?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-v4.0-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Uncensored_AI-8b5cf6?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![Tests](https://img.shields.io/badge/Tests-143%20Passed%20(100%25)-10b981?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![Security](https://img.shields.io/badge/Security-AST_Sandboxed-f43f5e?style=for-the-badge&logo=security&logoColor=white)](https://github.com/ark4ng3l/aether)
[![STIX 2.1](https://img.shields.io/badge/STIX-2.1_Compliant-f59e0b?style=for-the-badge)](https://oasis-open.github.io/cti-documentation/)
[![License](https://img.shields.io/badge/License-MIT-38bdf8?style=for-the-badge)](LICENSE)

<br/>

**🌍 Languages / زبان‌ها / Языки / 语言:**  
[English](README.md) • [فارسی (Persian)](README.fa.md) • [Русский (Russian)](README.ru.md) • [中文 (Chinese)](README.zh.md)

<br/>

[⚡ Quickstart](#-quickstart--launching) •
[🧠 Hierarchical Multi-Agent System](#-hierarchical-multi-agent-system-v40) •
[🩺 Cognitive Self-Healing Engine](#-autonomous-cognitive-self-healing-engine) •
[🛡️ Dual-Layer Sandbox](#-dual-layer-defense-sandbox) •
[🗺️ Multimodal Perception (Vision/Audio/Geo)](#-multimodal-perception--intelligence-pipelines) •
[📊 GraphRAG & Hybrid Memory](#-graphrag--hybrid-memory-fusion) •
[🌐 Multilingual UI (i18n)](#-multilingual-user-interface-i18n)

<br/>

```ascii
     ___      ______ _____ _    _ ______ _____  
    / _ \    |  ____|_   _| |  | |  ____|  __ \ 
   / /_\ \   | |__    | | | |__| | |__  | |__) |
  / / _ \ \  |  __|   | | |  __  |  __| |  _  / 
 / / / \ \ \ | |____ _| |_| |  | | |____| | \ \ 
/_/ /   \_\_\|______|_____|_|  |_|______|_|  \_\
       AUTONOMOUS COGNITIVE ENGINE // v4.0
```

</div>

---

## 🌟 Executive Overview

**AETHER v4.0** is an autonomous cyber intelligence, multimodal reconnaissance, and cognitive threat intelligence operating system. Built for security researchers and intelligence analysts, it transforms passive OSINT workflows into fully autonomous, hierarchical agent swarms with closed-loop reasoning:

$$\text{Goal Input} \longrightarrow \text{Tree-of-Thought Decomposition} \longrightarrow \text{Specialist Parallel Dispatch} \longrightarrow \text{Cognitive Self-Healing} \longrightarrow \text{Red-Team Critic Refutation} \longrightarrow \text{GraphRAG Dossier Synthesis}$$

Operating **100% locally via Ollama and public passive data sources**, AETHER guarantees complete operational security (OPSEC) and data privacy with zero cloud leaks or third-party tracking.

---

## 🧠 Hierarchical Multi-Agent System (v4.0)

AETHER implements the **Commander-Specialist-Critic** multi-agent cognitive architecture:

1. **Commander Agent (`CommanderAgent`)**:
   - Decomposes high-level intelligence objectives into atomic sub-task dependency graphs.
   - Evaluates execution branches using Tree-of-Thought (ToT) reasoning.
   - Orchestrates parallel asynchronous execution across specialist agents.
2. **Specialist Agents**:
   - **`NetworkSpecialist`**: DNS permutations, BGP/ASN routing, SSL/TLS SANs, Tech Stack fingerprinting, cloud bucket exposure.
   - **`VisionSpecialist`**: Optical Character Recognition (OCR), EXIF GPS coordinates, landmark heuristics, and scene understanding.
   - **`AudioSpecialist`**: Speech-to-text transcriptions with Whisper, entity timestamp extraction, acoustic intelligence.
   - **`ToolmakerSpecialist`**: Autonomous synthesis of custom Python query tools under AST static security verification.
3. **Red-Team Critic (`RedTeamCritic`)**:
   - Adversarially cross-examines all findings before ingestion to refute hallucinations and false positives.

---

## 🩺 Autonomous Cognitive Self-Healing Engine

When operations encounter obstacles (Cloudflare/WAF blocks, HTTP 429 rate-limits, format mismatches, or missing tools), AETHER autonomously diagnoses and repairs the failure:

- **Root Cause Analysis (RCA)**: Two-tier diagnostic engine classifying faults into 6 distinct categories (`INPUT_FORMAT_ERROR`, `RATE_LIMITED_OR_BLOCKED`, `TARGET_UNREACHABLE`, `TOOL_DEFICIENCY`, `CRITIC_REJECTION`, `UNKNOWN_TRANSIENT`).
- **Parameter Transmutation**: Automatically extracts hostnames from URLs, normalizes ports, and strips CIDR notation.
- **Passive Strategy Shift**: Automatically pivots from active scanning to passive repositories (Internet Archive CDX, DNS over HTTPS, BGPView) upon detecting defensive barriers.
- **Episodic Failure Memory**: Stores proven remedies to pre-emptively fix similar obstacles in future missions.

---

## 🛡️ Dual-Layer Defense Sandbox

Dynamic tools generated by the `ToolmakerSpecialist` undergo dual-layer execution containment:

1. **AST Static Security Analyzer (`aether/perception/tools/sandbox.py`)**:
   - Blocks blacklisted modules (`os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`).
   - Forbids dangerous dunder attributes (`__class__`, `__subclasses__`, `__globals__`).
   - Blocks dangerous builtins (`eval`, `exec`, `open`, `__import__`).
2. **Subprocess Isolation Runner (`aether/core/sandbox_runner.py`)**:
   - CLI execution in isolated subprocesses with stripped environment variables.
   - Enforces POSIX resource limits (256MB memory cap, 10s CPU cap) and strict timeout guards.

---

## 🗺️ Multimodal Perception & Intelligence Pipelines

- **Geo-Correlation (`GeoCorrelator`)**: Correlates EXIF metadata, Reverse Nominatim geolocation, and visual terrain cues.
- **Whisper Audio Intelligence (`WhisperAudioPipeline`)**: Transcribes audio intercepts and indexes spoken threat actor aliases.
- **Vision-Language Engine (`VisionLanguageIntelligenceEngine`)**: Multimodal scene understanding and document parsing.
- **Pipeline Chainer (`PipelineChainer`)**: Extracts IPs, domains, hashes, and emails from raw outputs and feeds them into downstream specialist tasks.

---

## 📊 GraphRAG & Hybrid Memory Fusion

- **GraphRAG Engine (`GraphRAG`)**: Performs multi-hop bi-directional entity traversals and community clustering.
- **Hybrid Knowledge Store (`HybridKnowledgeStore`)**: Combines dense semantic vector search (Qdrant) and graph topology using **Reciprocal Rank Fusion (RRF)**.

---

## 🌐 Multilingual User Interface (i18n)

AETHER features a fully localized user interface with instant language switching and dedicated RTL support:
- 🇺🇸 **English** (Default)
- 🇮🇷 **فارسی (Persian)** (Full RTL layout with Vazirmatn typography)
- 🇷🇺 **Русский (Russian)**
- 🇨🇳 **中文 (Chinese)**

---

## ⚡ Quickstart & Launching

### Prerequisites
- Python 3.11+
- Node.js 18+ (for building frontend)
- [Ollama](https://ollama.com) with models: `qwen2.5:7b`, `qwen2.5-coder:7b`, `qwen3-vl:8b` (optional)

### 1. Installation
```bash
git clone https://github.com/ark4ng3l/aether.git
cd aether
pip install -r requirements.txt
```

### 2. Launching AETHER
```bash
python run.py
```

The server will generate a secure session token and log the one-time bootstrap URL in your terminal:
```text
[bold green]================================================================[/bold green]
[bold green]  AETHER v4.0 — Autonomous Cyber-Intelligence Operator Ready    [/bold green]
[bold cyan]  Access UI at: http://127.0.0.1:8000/#token=<SECURE_SESSION_TOKEN>[/bold cyan]
[bold green]================================================================[/bold green]
```

Open the link in your browser to access the dashboard!

---

## 🧪 Running Automated Tests

```bash
python -m pytest tests/ -v
```

```text
================= 143 passed in 133.95s (100% Success) =================
```

---

## 📄 License & Responsible Use

This software is licensed under the [MIT License](LICENSE).  
**Notice:** AETHER is strictly designed for defensive threat intelligence, authorized security audits, and passive OSINT research. All tools operate strictly on public passive data sources.
