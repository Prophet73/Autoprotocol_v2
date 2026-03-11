export interface TourStep {
  target: string;
  title: string;
  description: string;
  placement: 'top' | 'bottom' | 'left' | 'right';
  path?: string;
  adminOnly?: boolean;
  viewerOnly?: boolean;
}

export const tourSteps: TourStep[] = [
  // === Основной интерфейс ===
  {
    target: '[data-tour="logo"]',
    title: 'Добро пожаловать в Autoprotocol!',
    description: 'Сервис автоматической расшифровки совещаний с генерацией протоколов, задач и аналитики.',
    placement: 'bottom',
    path: '/',
  },
  {
    target: '[data-tour="nav-upload"]',
    title: 'Загрузка файла',
    description: 'Загрузите аудио или видео запись совещания для обработки.',
    placement: 'right',
    path: '/',
  },
  {
    target: '[data-tour="project-code"]',
    title: 'Код проекта',
    description: 'Введите 4-значный код проекта с корпоративного портала. Если код не распознан — значит проект ещё не создан в системе. Обратитесь к администратору.',
    placement: 'bottom',
    path: '/',
  },
  {
    target: '[data-tour="dropzone"]',
    title: 'Зона загрузки',
    description: 'Перетащите файл сюда или нажмите для выбора. Поддерживаются форматы MP3, WAV, MP4, MKV и другие.',
    placement: 'bottom',
    path: '/',
  },
  {
    target: '[data-tour="artifact-options"]',
    title: 'Настройки генерации',
    description: 'Выберите какие документы создать: стенограмму, список задач, отчёт.',
    placement: 'top',
    path: '/',
  },
  {
    target: '[data-tour="nav-history"]',
    title: 'История обработок',
    description: 'Здесь хранятся все ваши обработанные файлы и их результаты.',
    placement: 'right',
    path: '/history',
  },

  // === Дашборд (viewer+) ===
  {
    target: '[data-tour="nav-dashboard"]',
    title: 'Дашборд',
    description: 'Аналитическая панель вашего департамента — календарь записей, типы встреч и последние результаты.',
    placement: 'right',
    viewerOnly: true,
  },
  {
    target: '[data-tour="dashboard-projects"]',
    title: 'Панель проектов',
    description: 'Список ваших проектов. Выберите проект, чтобы увидеть его календарь, пульс и проблемные вопросы.',
    placement: 'right',
    path: '/dashboard',
    viewerOnly: true,
  },
  {
    target: '[data-tour="dashboard-calendar"]',
    title: 'Календарь',
    description: 'Все обработанные совещания на календаре. Нажмите на запись, чтобы открыть подробный отчёт.',
    placement: 'bottom',
    path: '/dashboard',
    viewerOnly: true,
  },
  {
    target: '[data-tour="dashboard-scope"]',
    title: 'Мои записи / Департамент',
    description: 'Переключайтесь между своими записями и записями всего департамента.',
    placement: 'bottom',
    path: '/dashboard',
    viewerOnly: true,
  },
  {
    target: '[data-tour="dashboard-meeting-types"]',
    title: 'Типы встреч',
    description: 'Быстрый доступ к загрузке файла с уже выбранным типом совещания.',
    placement: 'top',
    path: '/dashboard',
    viewerOnly: true,
  },
  {
    target: '[data-tour="dashboard-recent"]',
    title: 'Проблемные вопросы',
    description: 'Список вопросов, требующих внимания. Отмечайте решённые, чтобы отслеживать прогресс.',
    placement: 'top',
    path: '/dashboard',
    viewerOnly: true,
  },

  // === Админ-панель (admin+) ===
  {
    target: '[data-tour="nav-admin"]',
    title: 'Админ-панель',
    description: 'Полное управление системой: пользователи, проекты, очередь задач, статистика и настройки.',
    placement: 'right',
    adminOnly: true,
    path: '/',
  },
  {
    target: '[data-tour="admin-dashboard"]',
    title: 'Обзор системы',
    description: 'Сводка по пользователям, транскрипциям, хранилищу и состоянию всех компонентов (БД, Redis, GPU, Celery).',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-jobs"]',
    title: 'Очередь задач',
    description: 'Мониторинг всех транскрипций в реальном времени. Можно отменять зависшие задачи.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-stats"]',
    title: 'Статистика',
    description: 'Детальная аналитика: графики по времени, расход токенов, стоимость, экспорт в Excel.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-users"]',
    title: 'Пользователи',
    description: 'Управление учётными записями: создание, роли, привязка к доменам и проектам.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-projects"]',
    title: 'Проекты',
    description: 'Создание и управление проектами. Здесь генерируются коды проектов для загрузки.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-settings"]',
    title: 'Настройки',
    description: 'Конфигурация системы: модели ИИ, лимиты, интеграции и параметры обработки.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },
  {
    target: '[data-tour="admin-logs"]',
    title: 'Логи ошибок',
    description: 'Журнал ошибок системы для диагностики проблем с обработкой файлов.',
    placement: 'right',
    path: '/admin',
    adminOnly: true,
  },

  // === Профиль (всегда последний) ===
  {
    target: '[data-tour="user-profile"]',
    title: 'Ваш профиль',
    description: 'Информация о вашей учётной записи и кнопка выхода из системы.',
    placement: 'right',
    path: '/',
  },
];
