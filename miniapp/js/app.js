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
        
        this.init();
    }

    init() {
        // Initialize Telegram WebApp
        this.tg.expand();
        this.tg.ready();
        
        // Detect user language
        this.detectLanguage();
        
        // Apply translations
        applyTranslations(this.currentLang);

        //Генерация реферальной ссылки
        this.referralLink = this.generateReferralLink();
        
        // Initialize earn button
        this.initButtons();
        
        // Update UI
        this.updateUI();
        
        // Log for debugging
        if (CONFIG.debugMode) {
            console.log('User:', this.tg.initDataUnsafe.user);
            console.log('Language:', this.currentLang);
        }
    }

    // Добавить этот метод в класс MiniApp
    showToast(message, type = 'info') { 
        // Используем глобальную функцию, которая работает с DOM, 
        // или переносим логику DOM сюда.
        // Для простоты, вызовем глобальную, но с проверкой:
        if (typeof showToast !== 'undefined') {
            showToast(message, type); // Предполагаем, что глобальная showToast принимает message и type
        } else {
            console.warn("showToast is missing, cannot display toast.");
        }
    }

    // Метод для загрузки всех начальных данных
    async loadInitialData() {
        if (!this.tg.initDataUnsafe.user?.id) {
            console.error("Telegram User ID is missing.");
            this.showToast('Ошибка: Не удалось получить ID пользователя.', 'error');
            return null;
        }

        const telegramId = this.tg.initDataUnsafe.user.id;
        
        try {
            // 1. Запрос статусов квестов и баланса
            const response = await fetch(`${this.baseApiUrl}/quest/statuses?telegram_id=${telegramId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.status === 'ok') {
                // 2. Обновление баланса
                this.state.setBalance(data.balance);
                
                // 3. Сохранение счетчиков
                this.state.setCounters(data.counters || {}); 
                
                // 4. Возвращаем статусы квестов для инициализации в quests.js
                return data.quests; // [{"quest_id": "...", "status": "visited"}, ...]
            } else {
                throw new Error(data.error || 'Unknown API error');
            }
        } catch (error) {
            console.error('Error fetching initial data:', error);
            this.showToast('Ошибка загрузки данных квестов.', 'error');
            return null;
        }
    }
    
    // [ИЗМЕНЕНИЕ] Метод для сохранения факта перехода на сервер
    async markQuestVisited(questId) {
        if (!this.tg.initDataUnsafe.user?.id) {
            this.showToast('Ошибка: ID пользователя отсутствует.', 'error');
            return { success: false };
        }
        
        const telegramId = this.tg.initDataUnsafe.user.id;
        
        try {
            const response = await fetch(`${this.baseApiUrl}/quest/visited`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    telegram_id: telegramId,
                    quest_id: questId,
                }),
            });
            
            if (!response.ok) {
                 throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return { success: data.status === 'ok' }; 
            
        } catch (error) {
            console.error(`Error marking quest ${questId} as visited:`, error);
            this.showToast('Ошибка сохранения статуса перехода.', 'error');
            return { success: false };
        }
    }

    // Для генерации ссылки
    generateReferralLink() {
        const userId = this.tg.initDataUnsafe.user?.id;
        const botUsername = CONFIG.botUsername; 
        const referralLink = this.referralLink;

        if (userId && botUsername) {
            // Формат: https://t.me/BOT_USERNAME/start?startapp=ref_USER_ID
            return `https://t.me/${botUsername}/start?startapp=ref_${userId}`;
        }
        // Запасной вариант, если ID или имя бота не найдены
        return 'https://t.me/your_mini_app_fallback?start=ref_error'; 
    }

    applyTelegramTheme() {
        const root = document.documentElement;
        const theme = this.tg.themeParams;
        
        if (theme.bg_color) root.style.setProperty('--bg-color', theme.bg_color);
        if (theme.text_color) root.style.setProperty('--text-primary', theme.text_color);
        if (theme.hint_color) root.style.setProperty('--text-secondary', theme.hint_color);
        if (theme.button_color) root.style.setProperty('--primary-color', theme.button_color);
        if (theme.secondary_bg_color) root.style.setProperty('--secondary-color', theme.secondary_bg_color);
        
        document.body.style.backgroundColor = theme.bg_color || '#ffffff';
    }

    detectLanguage() {
        const tgLang = this.tg.initDataUnsafe.user?.language_code;
        
        if (tgLang && translations[tgLang]) {
            this.currentLang = tgLang;
        } else if (tgLang && tgLang.startsWith('ru')) {
            this.currentLang = 'ru';
        } else if (translations[tgLang?.substring(0, 2)]) {
            this.currentLang = tgLang.substring(0, 2);
        }
    }

    initButtons() {
        // --- 1. Кнопки страницы "Заработок" (CASH) ---
        const earnBtn = document.getElementById('earn-btn');
        const addLimitBtn = document.getElementById('add-limit-btn');
        const cashOutBtn = document.getElementById('cash-out-btn'); // Кнопка вывода

        if (earnBtn) {
            earnBtn.addEventListener('click', () => {
                this.videoPlayer.open(); // Запуск видеоплеера
            });
        }

        if (addLimitBtn) {
            addLimitBtn.addEventListener('click', () => {
                this.navigation.navigateTo('quests'); // Переход на страницу квестов
            });
        }
        
        // Кнопка "ВЫВЕСТИ" (cash-out) обрабатывается в js/cashout.js, 
        // но оставим здесь на случай, если вы захотите добавить логику класса MiniApp.
        // if (cashOutBtn) {
        //     cashOutBtn.addEventListener('click', () => { 
        //         // showCashoutModal() вызывается из cashout.js
        //     });
        // }

        // --- 2. Кнопки страницы "Квесты" (Referral Actions) ---
        const copyBtn = document.getElementById('copy-link-btn');
        const inviteBtn = document.getElementById('invite-btn');

        const referralLink = this.referralLink;
        
        if (copyBtn) {
            copyBtn.addEventListener('click', async () => {
                try {
                    // Используем буфер обмена браузера
                    await navigator.clipboard.writeText(referralLink);
                    showToast('✅ Ссылка скопирована!');
                } catch (err) {
                    console.error('Не удалось скопировать текст:', err);
                    showToast('Ошибка копирования.');
                }
            });
        }
        
        // Логика кнопки "Пригласить" (Поделиться)
        if (inviteBtn && referralLink) {
            inviteBtn.addEventListener('click', () => {
                // Текст приглашения
                const inviteText = `👋 Присоединяйся и зарабатывай, просматривая видео! Это просто и быстро. Твоя реферальная ссылка:`; 
                const fullMessage = inviteText + ' ' + referralLink;

                // 1. ПРЕДПОЧТИТЕЛЬНЫЙ ВАРИАНТ (через pop-up шаринга Telegram SDK)
                if (this.tg && this.tg.showSharePopup) {
                    this.tg.showSharePopup({ 
                        message: fullMessage 
                    });
                    
                } else if (this.tg && this.tg.openTelegramLink) {
                    // 2. РЕЗЕРВНЫЙ ВАРИАНТ: Используем https://t.me/share/url
                    const encodedLink = encodeURIComponent(referralLink);
                    const encodedText = encodeURIComponent(inviteText);
                    const shareUrl = `https://t.me/share/url?url=${encodedLink}&text=${encodedText}`;

                    this.tg.openTelegramLink(shareUrl); 
                    showToast('🔗 Открыто окно выбора чата в Telegram.');

                } else {
                    // 3. ПОСЛЕДНИЙ ЗАПАСНОЙ ВАРИАНТ: Копирование в буфер
                    navigator.clipboard.writeText(fullMessage);
                    showToast('⚠️ Функция недоступна. Текст приглашения скопирован!');
                }
            });
        }
        
        // ❓ FAQ: Логика рендеринга и кликов
        if (typeof renderFaqList !== 'undefined') {
            renderFaqList();
        }

        // --- 4. Кнопка "Чат поддержки" (FAQ Page) ---
        const helpChatBtn = document.querySelector('.help-chat-btn');
        if (helpChatBtn) {
            helpChatBtn.addEventListener('click', () => {
                console.log('Кнопка "Чат поддержки" нажата. Имитация перехода.');
                // window.open('https://t.me/your_support_chat', '_blank'); 
            });
        }
    }

    updateUI() {
        document.getElementById('balance-value').textContent = this.state.getBalance();
        document.getElementById('today-count').textContent = this.state.getTodayCount() + " / " + this.state.getMaxCount();
        document.getElementById('total-earned').textContent = this.state.getTotalEarned();
    }

    onVideoComplete() {
        // Update state
        this.state.updateBalance(CONFIG.rewardAmount);
        
        // Show reward popup
        this.showRewardPopup();
        
        // Update UI
        this.updateUI();
        
        // Haptic feedback
        if (CONFIG.hapticFeedback && this.tg.HapticFeedback) {
            this.tg.HapticFeedback.notificationOccurred('success');
        }
    }

    showRewardPopup() {
        const popup = document.getElementById('reward-popup');
        popup.classList.add('active');
        
        setTimeout(() => {
            popup.classList.remove('active');
        }, 2000);
    }

    // app.js или App-подобный класс

async checkQuestStatus(questId) {
    // 1. Получаем необходимый telegram_id
    const user = window.Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.id) {
        console.error("Telegram User ID not found.");
        window.Telegram.WebApp.showAlert('Ошибка: Не удалось получить ID пользователя.');
        return { isCompleted: false, reward: 0 };
    }
    const telegramId = user.id;

    console.log(`[API] Checking quest ${questId} status for user ${telegramId}...`);
    
    try {
        // 2. Формируем URL и тело запроса
        const url = `/api/quest/check`;
        const response = await fetch(url, {
            method: 'POST', // Используем POST, как мы настроили в bot.py
            headers: {
                'Content-Type': 'application/json',
                // Для безопасности можно добавить токен или initData, но пока используем базовый POST
            },
            body: JSON.stringify({
                quest_id: questId,
                telegram_id: telegramId
            })
        });

        // 3. Проверяем HTTP-статус ответа
        if (!response.ok) {
            console.error(`HTTP error! Status: ${response.status}`);
            window.Telegram.WebApp.showAlert(`Ошибка сервера: ${response.status}`);
            return { isCompleted: false, reward: 0 };
        }

        // 4. Парсим JSON-ответ от сервера
        const result = await response.json();

        // 5. Обрабатываем ответ (сервер должен вернуть { isCompleted: bool, reward: number })
        if (result.status === 'error') {
            console.error(`Server logic error: ${result.error}`);
            window.Telegram.WebApp.showAlert(`Ошибка логики: ${result.error}`);
            return { isCompleted: false, reward: 0 };
        }
        
        return { 
            isCompleted: result.isCompleted || false, 
            reward: result.reward || 0 
        };

    } catch (error) {
        console.error("[API Error] Failed to check quest status:", error);
        window.Telegram.WebApp.showAlert('Ошибка подключения: Не удалось проверить статус квеста.');
        return { isCompleted: false, reward: 0 };
    }
}
}




// ==================== INITIALIZE APP ====================

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Инициализация Mini App
    const app = new MiniApp();
    
    // 2. Загрузка начальных данных с сервера
    const initialStatuses = await app.loadInitialData();
    
    if (initialStatuses) {
         // 3. Инициализация квестов с учетом серверных статусов
        const ALL_QUESTS_DATA = initQuests(initialStatuses, app);
        
        // 4. Рендеринг квестов и установка обработчиков
        renderQuests(ALL_QUESTS_DATA);
        setupQuestHandlers(app, ALL_QUESTS_DATA); // Передаем обновленные данные
    }

    app.updateUI(); 
    app.tg.ready();
});

// === УВЕДОМЛЕНИЕ (Toast Notification) ===
function showToast(message) {
    // Простая реализация всплывающего уведомления
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    
    // Скрыть через 3 секунды
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}





// ==================== FAQ ====================

function createFaqItem(title, description) {
    const item = document.createElement('div');
    item.className = 'faq-item';
    
    // Кнопка переключения (Toggle Button)
    const toggleButton = document.createElement('button');
    toggleButton.className = 'faq-toggle';
    
    // --- ИСПРАВЛЕНИЕ: Заменяем innerHTML на createElement и textContent ---
    
    // 1. Стрелка (Arrow)
    const arrowSpan = document.createElement('span');
    arrowSpan.className = 'faq-arrow';
    arrowSpan.textContent = '❯'; // Символ стрелки
    
    // 2. Заголовок (Title)
    const titleSpan = document.createElement('span');
    titleSpan.className = 'faq-title';
    titleSpan.textContent = title;
    
    // Сборка toggleButton
    toggleButton.appendChild(arrowSpan);
    toggleButton.appendChild(titleSpan);
    // -------------------------------------------------------------------

    // Обертка для контента (для анимации)
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'faq-content-wrapper';
    
    const descriptionParagraph = document.createElement('p');
    descriptionParagraph.className = 'faq-description';
    descriptionParagraph.textContent = description;
    
    contentWrapper.appendChild(descriptionParagraph);

    // Сборка элемента
    item.appendChild(toggleButton);
    item.appendChild(contentWrapper);
    
    return item;
}

function renderFaqList() {
    const faqListContainer = document.getElementById('faq-list');
    
    // Очищаем контейнер перед добавлением новых элементов (если он не пуст)
    if (faqListContainer) {
        faqListContainer.innerHTML = ''; 
        
        // Перебираем массив данных и создаем элементы
        faqData.forEach(item => {
            // Используем исправленный createFaqItem
            const faqElement = createFaqItem(item.title, item.description); 
            faqListContainer.appendChild(faqElement);
        });
    }

    // После рендеринга можно настроить обработчики событий
    // Эта функция должна быть определена где-то еще в вашем коде (например, в app.js)
    setupFaqToggle(); 
}

function setupFaqToggle() {
    const faqList = document.getElementById('faq-list');
    if (!faqList) return;

    // Находим все элементы FAQ и навешиваем слушатель на весь контейнер
    faqList.addEventListener('click', (e) => {
        const toggleButton = e.target.closest('.faq-toggle');

        if (!toggleButton) return;

        const faqItem = toggleButton.closest('.faq-item');
        const contentWrapper = faqItem.querySelector('.faq-content-wrapper');

        const isActive = faqItem.classList.contains('active');

        // Закрываем все остальные элементы
        document.querySelectorAll('.faq-item.active').forEach(item => {
            if (item !== faqItem) {
                item.classList.remove('active');
                item.querySelector('.faq-content-wrapper').style.maxHeight = 0;
            }
        });

        if (isActive) {
            // Закрываем
            faqItem.classList.remove('active');
            contentWrapper.style.maxHeight = 0;
        } else {
            // Открываем
            faqItem.classList.add('active');
            // Устанавливаем max-height
            contentWrapper.style.maxHeight = contentWrapper.scrollHeight + 'px';
        }
    });
}




const faqData = [
    { 
        title: "Как это работает?", 
        description: "Наше приложение позволяет зарабатывать, просматривая короткие рекламные видеоролики. За каждый просмотр вам начисляется вознаграждение на внутренний баланс." 
    },
    { 
        title: "Как получить награду?", 
        description: "Награда начисляется автоматически после полного просмотра видео. Накопленные средства можно вывести на ваш крипто-кошелек или другую платежную систему по достижении минимальной суммы." 
    },
    { 
        title: "Техническая поддержка", 
        description: "Если у вас возникли вопросы или проблемы, вы можете связаться с нашей службой поддержки через кнопку 'Чат поддержки' внизу страницы." 
    },
    { 
        title: "Как получить награду?", 
        description: "Награда начисляется автоматически после полного просмотра видео. Накопленные средства можно вывести на ваш крипто-кошелек или другую платежную систему по достижении минимальной суммы." 
    },
    { 
        title: "Техническая поддержка", 
        description: "Если у вас возникли вопросы или проблемы, вы можете связаться с нашей службой поддержки через кнопку 'Чат поддержки' внизу страницы." 
    },
    { 
        title: "Как получить награду?", 
        description: "Награда начисляется автоматически после полного просмотра видео. Накопленные средства можно вывести на ваш крипто-кошелек или другую платежную систему по достижении минимальной суммы." 
    },
    { 
        title: "Техническая поддержка", 
        description: "Если у вас возникли вопросы или проблемы, вы можете связаться с нашей службой поддержки через кнопку 'Чат поддержки' внизу страницы." 
    },
    { 
        title: "Как получить награду?", 
        description: "Награда начисляется автоматически после полного просмотра видео. Накопленные средства можно вывести на ваш крипто-кошелек или другую платежную систему по достижении минимальной суммы." 
    },
    { 
        title: "Техническая поддержка", 
        description: "Если у вас возникли вопросы или проблемы, вы можете связаться с нашей службой поддержки через кнопку 'Чат поддержки' внизу страницы." 
    },
    { 
        title: "Минимальная сумма для вывода", 
        description: "Минимальный порог для вывода составляет $10.00." 
    }
];

// Сделайте этот массив доступным для других файлов, например, экспортируя его
// export { faqData };




