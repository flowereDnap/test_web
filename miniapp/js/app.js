// ==================== MAIN APP ====================
class MiniApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.currentLang = CONFIG.defaultLanguage;
        this.state = new AppState();
        this.videoPlayer = new VideoPlayer(this);
        this.navigation = new Navigation(this);
        this.referralLink = null;
        this.baseApiUrl = '/api';
        
        this.allQuestsData = []; // Хранилище объектов квестов из quests.js
        
        this.init();
    }

    /** Геттер для быстрого доступа к ID пользователя */
    get userId() {
        return this.tg.initDataUnsafe?.user?.id || 0;
    }

    async init() {
        this.tg.expand();
        this.tg.ready();
        
        this.detectLanguage();
        applyTranslations(this.currentLang);

        this.referralLink = this.generateReferralLink();
        this.initButtons();
        this.renderFAQ(); // Отрисовка FAQ при запуске
        
        // Первичная загрузка баланса и счетчиков
        await this.state.loadState(this.userId);
        this.updateUI();
        
        if (CONFIG.debugMode) {
            console.log('App Initialized. User:', this.userId);
        }
    }

    /** * Универсальный метод для API. 
     * Автоматически подставляет telegram_id и обрабатывает ошибки.
     */
    async apiRequest(endpoint, method = 'POST', data = {}) {
        try {
            let url = `${this.baseApiUrl}${endpoint}`;
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' }
            };

            if (method === 'GET') {
                url += `?telegram_id=${this.userId}`;
            } else {
                options.body = JSON.stringify({ ...data, telegram_id: this.userId });
            }

            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            return { success: false, isCompleted: false };
        }
    }

    /** Загрузка и отрисовка квестов */
    async loadAndRenderQuests() {
        const container = document.getElementById('quests-list');
        if (!container) return;

        container.textContent = 'Загрузка заданий...';

        try {
            // Исправленный эндпоинт из твоего бота
            const serverStatuses = await this.apiRequest('/quest/statuses', 'GET');
            
            // Инициализация классов из quests.js
            this.allQuestsData = await initQuests(serverStatuses, this);
            renderQuestList(this.allQuestsData);
            setupQuestHandlers(this, this.allQuestsData);
        } catch (e) {
            container.textContent = 'Не удалось загрузить задания.';
        }
    }

    // --- Методы взаимодействия (для вызова из quests.js) ---

    async markQuestVisited(questId) {
        return await this.apiRequest('/quest/visited', 'POST', { quest_id: questId });
    }

    async verifyQuest(questId) {
        return await this.apiRequest('/quest/verify', 'POST', { quest_id: questId });
    }

    /** Инициализация всех кнопок приложения */
    initButtons() {
        // 1. Кнопка "Заработать" (Видео)
        document.getElementById('earn-btn')?.addEventListener('click', () => {
            this.videoPlayer.open();
        });

        // 2. Кнопка "Увеличить Лимит"
        document.getElementById('add-limit-btn')?.addEventListener('click', () => {
            this.showToast('Задания для увеличения лимита скоро появятся!', 'info');
        });

        // 3. Кнопка "ВЫВЕСТИ"
        document.getElementById('cash-out-btn')?.addEventListener('click', () => {
            // Если у тебя инициализирован класс Cashout в cashout.js
            if (window.cashout) {
                window.cashout.open(); 
            } else {
                this.showToast('Модуль вывода загружается...', 'info');
            }
        });

        // 4. Реферальные кнопки (Квесты)
        document.getElementById('copy-link-btn')?.addEventListener('click', () => {
            this.copyReferralLink();
        });

        document.getElementById('invite-btn')?.addEventListener('click', () => {
            const text = encodeURIComponent(`Смотри видео и зарабатывай вместе со мной! 💰`);
            const url = `https://t.me/share/url?url=${encodeURIComponent(this.referralLink)}&text=${text}`;
            this.tg.openTelegramLink(url);
        });

        // 5. Кнопка "Чат поддержки" (ПО ИСПРАВЛЕННОМУ СЕЛЕКТОРУ)
        const supportBtn = document.querySelector('.help-chat-btn');
        if (supportBtn) {
            supportBtn.addEventListener('click', () => {
                const supportBotUsername = CONFIG.supportBotUsername || 'adds_FAQ_bot'; // Замени на реальный ник
                const url = `https://t.me/${supportBotUsername}`;

                this.tg.openTelegramLink(url);

                if (this.tg.HapticFeedback) {
                    this.tg.HapticFeedback.impactOccurred('medium');
                }
            });
        }
    }

    /** Показ окна награды после просмотра рекламы */
    showRewardPopup(amount) {
        const popup = document.getElementById('reward-popup');
        const display = document.getElementById('reward-amount-display');
        if (!popup || !display) return;

        display.textContent = `+$${amount.toFixed(2)}`;
        popup.classList.add('show');
        
        this.tg.HapticFeedback?.notificationOccurred('success');

        const closeBtn = popup.querySelector('.primary-btn');
        if (closeBtn) {
            closeBtn.onclick = () => {
                popup.classList.remove('show');
                this.updateUI();
            };
        }
    }

    /** Рендеринг FAQ (без innerHTML) */
    renderFAQ() {
        const faqListContainer = document.getElementById('faq-list');
        if (!faqListContainer || typeof faqData === 'undefined') return;

        // 1. Очистка контейнера
        faqListContainer.innerHTML = ''; 

        // 2. Рендеринг (твой оригинальный алгоритм из createFaqItem)
        faqData.forEach(item => {
            const faqItem = document.createElement('div');
            faqItem.className = 'faq-item';

            const toggleButton = document.createElement('button');
            toggleButton.className = 'faq-toggle';

            const arrowSpan = document.createElement('span');
            arrowSpan.className = 'faq-arrow';
            arrowSpan.textContent = '❯';

            const titleSpan = document.createElement('span');
            titleSpan.className = 'faq-title';
            titleSpan.textContent = item.title;

            toggleButton.appendChild(arrowSpan);
            toggleButton.appendChild(titleSpan);

            const contentWrapper = document.createElement('div');
            contentWrapper.className = 'faq-content-wrapper';

            const descriptionParagraph = document.createElement('p');
            descriptionParagraph.className = 'faq-description';
            descriptionParagraph.textContent = item.description;

            contentWrapper.appendChild(descriptionParagraph);
            faqItem.appendChild(toggleButton);
            faqItem.appendChild(contentWrapper);

            faqListContainer.appendChild(faqItem);
        });

        // 3. Инициализация кликов (твой оригинальный setupFaqToggle)
        // Удаляем старый слушатель, если он был, чтобы не дублировать
        faqListContainer.onclick = null; 

        faqListContainer.addEventListener('click', (e) => {
            const toggleButton = e.target.closest('.faq-toggle');
            if (!toggleButton) return;

            const faqItem = toggleButton.closest('.faq-item');
            const contentWrapper = faqItem.querySelector('.faq-content-wrapper');
            const isActive = faqItem.classList.contains('active');

            // Закрываем все остальные (аккордеон)
            document.querySelectorAll('.faq-item.active').forEach(openItem => {
                if (openItem !== faqItem) {
                    openItem.classList.remove('active');
                    openItem.querySelector('.faq-content-wrapper').style.maxHeight = 0;
                }
            });

            if (isActive) {
                faqItem.classList.remove('active');
                contentWrapper.style.maxHeight = 0;
            } else {
                faqItem.classList.add('active');
                // ВАЖНО: Твой расчет высоты для плавной анимации
                contentWrapper.style.maxHeight = contentWrapper.scrollHeight + 'px';
            }

            // Добавляем тактильный отклик от Telegram
            if (this.tg.HapticFeedback) {
                this.tg.HapticFeedback.impactOccurred('light');
            }
        });
    }

    updateUI() {
        document.querySelectorAll('.balance-amount').forEach(el => {
            el.textContent = this.state.getBalance().toFixed(2);
        });

        const videoCounter = document.getElementById('video-counter');
        if (videoCounter) {
            videoCounter.textContent = this.state.getCounter('videos_watched');
        }
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        if (!toast) return;

        toast.textContent = message;
        toast.className = `toast ${type} show`;

        if (type === 'success') this.tg.HapticFeedback?.notificationOccurred('success');
        if (type === 'error') this.tg.HapticFeedback?.notificationOccurred('error');

        setTimeout(() => { toast.className = 'toast'; }, 3000);
    }

    detectLanguage() {
        const tgLang = this.tg.initDataUnsafe?.user?.language_code;
        if (tgLang === 'ru' || tgLang === 'en') {
            this.currentLang = tgLang;
        }
    }

    generateReferralLink() {
        return `https://t.me/${CONFIG.botUsername || 'bot'}?start=ref_${this.userId}`;
    }

    copyReferralLink() {
        const temp = document.createElement('input');
        temp.value = this.referralLink;
        document.body.appendChild(temp);
        temp.select();
        document.execCommand('copy');
        document.body.removeChild(temp);
        this.showToast('Ссылка скопирована!', 'success');
    }
}


// Данные FAQ
const faqData = [
    { title: "Как это работает?", description: "Вы смотрите короткие видео и получаете за это вознаграждение на свой баланс." },
    { title: "Как вывести средства?", description: "Вывод доступен при достижении минимальной суммы в $10.00 через раздел кошелька." },
    { title: "Техническая поддержка", description: "Свяжитесь с нами через чат поддержки в профиле, если возникли вопросы." }
];

// Запуск
window.addEventListener('DOMContentLoaded', () => {
    window.app = new MiniApp();
});