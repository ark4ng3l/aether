export type SupportedLocale = 'en' | 'fa' | 'ru' | 'zh'

export interface LocaleMeta {
  code: SupportedLocale
  name: string
  nativeName: string
  dir: 'ltr' | 'rtl'
  flag: string
}

export const SUPPORTED_LOCALES: LocaleMeta[] = [
  { code: 'en', name: 'English', nativeName: 'English', dir: 'ltr', flag: '🇺🇸' },
  { code: 'fa', name: 'Persian', nativeName: 'فارسی', dir: 'rtl', flag: '🇮🇷' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский', dir: 'ltr', flag: '🇷🇺' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', dir: 'ltr', flag: '🇨🇳' },
]

export const translations: Record<SupportedLocale, Record<string, string>> = {
  en: {
    // Shell & Navigation
    'nav.workspace': 'Workspace',
    'nav.search': 'Search or jump to...',
    'nav.overview': 'Overview',
    'nav.graph': 'Graph',
    'nav.timeline': 'Timeline',
    'nav.map': 'Map & Geo',
    'nav.arsenal': 'Arsenal',
    'nav.vision': 'Vision AI',
    'nav.dossier': 'Dossier',
    'nav.console': 'Console',
    'nav.newInvestigation': 'New Investigation',
    'nav.expandSidebar': 'Expand sidebar',
    'nav.collapseSidebar': 'Collapse sidebar',
    'nav.keyboardShortcuts': 'Keyboard Shortcuts',
    'nav.settings': 'Settings',
    'nav.theme': 'Theme',
    'nav.language': 'Language',

    // Statuses
    'status.idle': 'Idle',
    'status.planning': 'Planning',
    'status.collecting': 'Collecting',
    'status.reasoning': 'Reasoning',
    'status.completed': 'Completed',
    'status.failed': 'Failed',
    'status.active': 'Active',

    // Common Actions
    'action.save': 'Save',
    'action.cancel': 'Cancel',
    'action.delete': 'Delete',
    'action.create': 'Create',
    'action.run': 'Run Mission',
    'action.stop': 'Stop',
    'action.purge': 'Purge',
    'action.export': 'Export',
    'action.filter': 'Filter...',
    'action.close': 'Close',
    'action.loading': 'Loading...',
    'action.execute': 'Execute',

    // Investigation & Projects
    'project.newTitle': 'Initiate Investigation',
    'project.name': 'Operation Name',
    'project.namePlaceholder': 'e.g. Operation Shadow Ghost',
    'project.targetSeed': 'Target Seed (Domain, IP, Handle, Email)',
    'project.targetSeedPlaceholder': 'e.g. target.com, 192.168.1.1, @threat_actor',
    'project.targetType': 'Target Entity Type',
    'project.briefing': 'Mission Briefing & Rules of Engagement',
    'project.briefingPlaceholder': 'Provide any known threat actor aliases, infrastructure hints, or intelligence requirements...',
    'project.noProjects': 'No investigations found. Create one to begin.',
    'project.purgeConfirm': 'Are you sure you want to permanently purge this project and all its collected graph nodes, vector embeddings, and telemetry?',

    // Metrics & Intelligence
    'metrics.entities': 'Entities Discovered',
    'metrics.relations': 'Correlations & Edges',
    'metrics.tasks': 'Completed Tasks',
    'metrics.threatLevel': 'Threat Severity',
    'metrics.confidence': 'Cognitive Confidence',
    'metrics.dossierReady': 'Dossier Generated',

    // Cognitive Self-Healing
    'healing.title': 'Cognitive Self-Healing & Resilience',
    'healing.rca': 'Root Cause Analysis',
    'healing.status': 'Self-Healed',
    'healing.strategy': 'Remediation Strategy',
    'healing.transmuted': 'Transmuted Parameters',
    'healing.shifted': 'Shifted to Passive Mirror',
    'healing.synthesized': 'Synthesized Dynamic Tool',

    // Modals & Settings
    'settings.title': 'System & Neural Configuration',
    'settings.modelProvider': 'Model Provider',
    'settings.ollamaUrl': 'Ollama Base URL',
    'settings.reasoningModel': 'Cognitive Reasoning Model',
    'settings.visionModel': 'Vision Language Model',
    'settings.saveSuccess': 'Settings successfully saved',
    'settings.updates': 'Check for Updates',

    // Notifications & Shortcuts
    'notifications.title': 'Real-Time Telemetry',
    'notifications.empty': 'No new alerts',
    'notifications.clear': 'Clear All',
    'shortcuts.title': 'Keyboard Shortcuts',
  },

  fa: {
    // Shell & Navigation
    'nav.workspace': 'فضای عملیاتی',
    'nav.search': 'جستجو یا پرش سریع...',
    'nav.overview': 'نمای کلی',
    'nav.graph': 'گراف هویت‌ها',
    'nav.timeline': 'خط زمانی',
    'nav.map': 'نقشه و ژئولوکیشن',
    'nav.arsenal': 'زرادخانه ابزارها',
    'nav.vision': 'هوش بصری',
    'nav.dossier': 'پرونده اطلاعاتی',
    'nav.console': 'کنسول زنده',
    'nav.newInvestigation': 'تحقیق جدید',
    'nav.expandSidebar': 'باز کردن نوار کناری',
    'nav.collapseSidebar': 'بستن نوار کناری',
    'nav.keyboardShortcuts': 'کلیدهای میانبر',
    'nav.settings': 'تنظیمات سیستم',
    'nav.theme': 'پوسته',
    'nav.language': 'زبان',

    // Statuses
    'status.idle': 'آماده به کار',
    'status.planning': 'برنامه‌ریزی مأموریت',
    'status.collecting': 'جمع‌آوری داده',
    'status.reasoning': 'استنتاج شناختی',
    'status.completed': 'تکمیل شده',
    'status.failed': 'ناموفق',
    'status.active': 'فعال',

    // Common Actions
    'action.save': 'ذخیره',
    'action.cancel': 'انصراف',
    'action.delete': 'حذف',
    'action.create': 'ایجاد',
    'action.run': 'شروع مأموریت',
    'action.stop': 'توقف',
    'action.purge': 'پاک‌سازی کامل',
    'action.export': 'خروجی',
    'action.filter': 'فیلتر...',
    'action.close': 'بستن',
    'action.loading': 'در حال بارگذاری...',
    'action.execute': 'اجرا',

    // Investigation & Projects
    'project.newTitle': 'آغاز عملیات اطلاعاتی جدید',
    'project.name': 'نام عملیات',
    'project.namePlaceholder': 'مثال: عملیات شبح سیاه',
    'project.targetSeed': 'هسته هدف (دامنه، IP، نام کاربری، ایمیل)',
    'project.targetSeedPlaceholder': 'مثال: target.com، 192.168.1.1، @threat_actor',
    'project.targetType': 'نوع هویت هدف',
    'project.briefing': 'شرح مأموریت و قواعد عملیاتی',
    'project.briefingPlaceholder': 'نام‌های مستعار، اطلاعات زیرساختی یا الزامات اطلاعاتی شناخته‌شده را وارد کنید...',
    'project.noProjects': 'هیچ پروژه‌ای یافت نشد. برای شروع، عملیات جدیدی بسازید.',
    'project.purgeConfirm': 'آیا مطمئن هستید که می‌خواهید این عملیات و تمام گره‌های گراف، بردارهای حافظه و داده‌های جمع‌آوری‌شده را برای همیشه حذف کنید؟',

    // Metrics & Intelligence
    'metrics.entities': 'هویت‌های کشف‌شده',
    'metrics.relations': 'روابط و پیوندها',
    'metrics.tasks': 'وظایف انجام‌شده',
    'metrics.threatLevel': 'سطح تهدید',
    'metrics.confidence': 'اطمینان شناختی',
    'metrics.dossierReady': 'پرونده نهایی آماده است',

    // Cognitive Self-Healing
    'healing.title': 'خودترمیمی و پایداری شناختی',
    'healing.rca': 'علت‌یابی ریشه‌ای (RCA)',
    'healing.status': 'خودترمیم‌شده',
    'healing.strategy': 'استراتژی ترمیمی',
    'healing.transmuted': 'پارامترهای تبدیل‌شده',
    'healing.shifted': 'انتقال به مخزن پسیو',
    'healing.synthesized': 'سنتز خودکار ابزار جدید',

    // Modals & Settings
    'settings.title': 'پیکربندی سیستم و مدل‌های عصبی',
    'settings.modelProvider': 'تأمین‌کننده مدل',
    'settings.ollamaUrl': 'آدرس سرور Ollama',
    'settings.reasoningModel': 'مدل استنتاج و فرماندهی',
    'settings.visionModel': 'مدل هوش بصری (VLM)',
    'settings.saveSuccess': 'تنظیمات با موفقیت ذخیره شد',
    'settings.updates': 'بررسی به‌روزرسانی‌ها',

    // Notifications & Shortcuts
    'notifications.title': 'تلمتری و هشدارهای زنده',
    'notifications.empty': 'هیچ هشدار جدیدی وجود ندارد',
    'notifications.clear': 'پاک‌سازی همه',
    'shortcuts.title': 'راهنمای کلیدهای میانبر',
  },

  ru: {
    // Shell & Navigation
    'nav.workspace': 'Рабочее пространство',
    'nav.search': 'Поиск или быстрый переход...',
    'nav.overview': 'Обзор',
    'nav.graph': 'Граф связей',
    'nav.timeline': 'Хронология',
    'nav.map': 'Карта и гео',
    'nav.arsenal': 'Инструменты',
    'nav.vision': 'Компьютерное зрение',
    'nav.dossier': 'Досье',
    'nav.console': 'Консоль',
    'nav.newInvestigation': 'Новое расследование',
    'nav.expandSidebar': 'Развернуть меню',
    'nav.collapseSidebar': 'Свернуть меню',
    'nav.keyboardShortcuts': 'Горячие клавиши',
    'nav.settings': 'Настройки',
    'nav.theme': 'Тема',
    'nav.language': 'Язык',

    // Statuses
    'status.idle': 'Ожидание',
    'status.planning': 'Планирование',
    'status.collecting': 'Сбор данных',
    'status.reasoning': 'Анализ',
    'status.completed': 'Завершено',
    'status.failed': 'Ошибка',
    'status.active': 'Активно',

    // Common Actions
    'action.save': 'Сохранить',
    'action.cancel': 'Отмена',
    'action.delete': 'Удалить',
    'action.create': 'Создать',
    'action.run': 'Запустить',
    'action.stop': 'Остановить',
    'action.purge': 'Очистить',
    'action.export': 'Экспорт',
    'action.filter': 'Фильтр...',
    'action.close': 'Закрыть',
    'action.loading': 'Загрузка...',
    'action.execute': 'Выполнить',

    // Investigation & Projects
    'project.newTitle': 'Начать новое расследование',
    'project.name': 'Название операции',
    'project.namePlaceholder': 'например: Операция Shadow Ghost',
    'project.targetSeed': 'Цель (Домен, IP, Никнейм, Email)',
    'project.targetSeedPlaceholder': 'например: target.com, 192.168.1.1, @threat_actor',
    'project.targetType': 'Тип сущности цели',
    'project.briefing': 'Брифинг и правила операции',
    'project.briefingPlaceholder': 'Введите известные псевдонимы, детали инфраструктуры или требования...',
    'project.noProjects': 'Расследования не найдены. Создайте новое для начала работы.',
    'project.purgeConfirm': 'Вы уверены, что хотите навсегда удалить этот проект и все собранные данные графа и векторы?',

    // Metrics & Intelligence
    'metrics.entities': 'Обнаружено сущностей',
    'metrics.relations': 'Связей и ребер',
    'metrics.tasks': 'Выполнено задач',
    'metrics.threatLevel': 'Уровень угрозы',
    'metrics.confidence': 'Уверенность модели',
    'metrics.dossierReady': 'Досье сформировано',

    // Cognitive Self-Healing
    'healing.title': 'Самовосстановление и устойчивость',
    'healing.rca': 'Анализ первопричин (RCA)',
    'healing.status': 'Восстановлено',
    'healing.strategy': 'Стратегия исправления',
    'healing.transmuted': 'Скорректированные параметры',
    'healing.shifted': 'Переход на пассивные зеркала',
    'healing.synthesized': 'Синтезирован динамический инструмент',

    // Modals & Settings
    'settings.title': 'Конфигурация нейросетей и системы',
    'settings.modelProvider': 'Провайдер моделей',
    'settings.ollamaUrl': 'URL-адрес Ollama',
    'settings.reasoningModel': 'Модель рассуждений',
    'settings.visionModel': 'Модель компьютерного зрения',
    'settings.saveSuccess': 'Настройки успешно сохранены',
    'settings.updates': 'Проверка обновлений',

    // Notifications & Shortcuts
    'notifications.title': 'Телеметрия в реальном времени',
    'notifications.empty': 'Нет новых оповещений',
    'notifications.clear': 'Очистить все',
    'shortcuts.title': 'Справка по горячим клавишам',
  },

  zh: {
    // Shell & Navigation
    'nav.workspace': '工作空间',
    'nav.search': '搜索或快速跳转...',
    'nav.overview': '总览',
    'nav.graph': '实体图谱',
    'nav.timeline': '时间线',
    'nav.map': '地理态势',
    'nav.arsenal': '工具军械库',
    'nav.vision': '视觉智能',
    'nav.dossier': '情报卷宗',
    'nav.console': '实时控制台',
    'nav.newInvestigation': '新建调查',
    'nav.expandSidebar': '展开侧边栏',
    'nav.collapseSidebar': '折叠侧边栏',
    'nav.keyboardShortcuts': '快捷键',
    'nav.settings': '系统设置',
    'nav.theme': '主题',
    'nav.language': '语言',

    // Statuses
    'status.idle': '待命',
    'status.planning': '规划中',
    'status.collecting': '采集中',
    'status.reasoning': '智能推理中',
    'status.completed': '已完成',
    'status.failed': '失败',
    'status.active': '运行中',

    // Common Actions
    'action.save': '保存',
    'action.cancel': '取消',
    'action.delete': '删除',
    'action.create': '创建',
    'action.run': '启动任务',
    'action.stop': '停止',
    'action.purge': '彻底清除',
    'action.export': '导出',
    'action.filter': '过滤...',
    'action.close': '关闭',
    'action.loading': '加载中...',
    'action.execute': '执行',

    // Investigation & Projects
    'project.newTitle': '发起新情报调查',
    'project.name': '行动名称',
    'project.namePlaceholder': '例如：暗影幽灵行动',
    'project.targetSeed': '目标种子 (域名、IP、社交账号、邮箱)',
    'project.targetSeedPlaceholder': '例如：target.com, 192.168.1.1, @threat_actor',
    'project.targetType': '目标实体类型',
    'project.briefing': '任务简报与交战规则',
    'project.briefingPlaceholder': '输入已知的威胁实体别名、基础设施线索或情报需求...',
    'project.noProjects': '未找到任何调查项目。请创建新项目以开始。',
    'project.purgeConfirm': '您确定要永久清除此项目及其所有图谱节点、向量嵌入和遥测数据吗？',

    // Metrics & Intelligence
    'metrics.entities': '已发现实体',
    'metrics.relations': '关联与边',
    'metrics.tasks': '已完成任务',
    'metrics.threatLevel': '威胁级别',
    'metrics.confidence': '认知置信度',
    'metrics.dossierReady': '卷宗已就绪',

    // Cognitive Self-Healing
    'healing.title': '认知自我修复与韧性系统',
    'healing.rca': '根本原因分析 (RCA)',
    'healing.status': '已自愈修复',
    'healing.strategy': '修复策略',
    'healing.transmuted': '已转换输入参数',
    'healing.shifted': '已切换至被动镜像',
    'healing.synthesized': '动态合成新工具',

    // Modals & Settings
    'settings.title': '系统与神经推理配置',
    'settings.modelProvider': '模型提供商',
    'settings.ollamaUrl': 'Ollama 服务地址',
    'settings.reasoningModel': '推理决策模型',
    'settings.visionModel': '视觉语言模型',
    'settings.saveSuccess': '设置已成功保存',
    'settings.updates': '检查更新',

    // Notifications & Shortcuts
    'notifications.title': '实时情报遥测',
    'notifications.empty': '暂无新通知',
    'notifications.clear': '清空全部',
    'shortcuts.title': '键盘快捷键指南',
  },
}
