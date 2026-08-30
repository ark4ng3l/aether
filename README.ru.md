<div align="center">

# 🌐 AETHER v4.0: Автономный оператор киберразведки
**Иерархическая мультиагентная система • Мультимодальное восприятие • Когнитивное самовосстановление • GraphRAG**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-38bdf8?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-v4.0-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Uncensored_AI-8b5cf6?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![Tests](https://img.shields.io/badge/Tests-143%20Passed%20(100%25)-10b981?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![Лицензия](https://img.shields.io/badge/License-MIT-38bdf8?style=for-the-badge)](LICENSE)

<br/>

**🌍 Языки / Languages / زبان‌ها / 语言:**  
[English](README.md) • [فارسی (Persian)](README.fa.md) • [Русский (Russian)](README.ru.md) • [中文 (Chinese)](README.zh.md)

</div>

---

## 🌟 Обзор проекта

**AETHER v4.0** — автономная платформа для киберразведки, анализа угроз и пассивного сбора данных (OSINT). Система работает **100% локально на базе нейросетей Ollama**, гарантируя полную конфиденциальность (OPSEC) без передачи данных во внешние облачные сервисы.

### Ключевые возможности v4.0:
1. **Иерархическая мультиагентная система**:
   - `CommanderAgent` (Планирование и декомпозиция задач по методу Tree-of-Thought)
   - Специалисты: `NetworkSpecialist`, `VisionSpecialist`, `AudioSpecialist`, `ToolmakerSpecialist`
   - `RedTeamCritic` (Верификация находок и защита от галлюцинаций модели)
2. **Когнитивное самовосстановление (Self-Healing Engine)**:
   - Анализ первопричин ошибок (RCA)
   - Автоматическая нормализация параметров (Transmutation)
   - Переключение на пассивные зеркала (Wayback, Public DNS, BGPView) при блокировках и WAF
3. **Двухуровневая изолированная песочница (AST & Subprocess Sandbox)**:
   - Статический анализ AST против вредоносных модулей и функций
   - Выполнение динамических скриптов в subprocess с ограничениями по памяти (256MB) и времени
4. **Многоязычный интерфейс**:
   - Поддержка Русского, Английского, Персидского (с RTL) и Китайского языков

---

## ⚡ Быстрый старт

```bash
git clone https://github.com/ark4ng3l/aether.git
cd aether
pip install -r requirements.txt
python run.py
```

После запуска в консоли появится защищенная одноразовая ссылка для входа в веб-интерфейс:
`http://127.0.0.1:8000/#token=<SESSION_TOKEN>`
