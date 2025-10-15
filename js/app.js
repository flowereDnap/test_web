// ==================== MAIN APP ====================
class MiniApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.currentLang = CONFIG.defaultLanguage;
        this.state = new AppState();
        this.videoPlayer = new VideoPlayer(this);
        this.navigation = new Navigation(this);
        
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
        const earnBtn = document.getElementById('earn-btn');
        const addLimitBtn = document.getElementById('add-limit-btn');
        const cashOutBtn = document.getElementById('cash-out-btn');
        const copyBtn = document.getElementById('copy-link-btn');
        const inviteBtn = document.getElementById('invite-btn');
        const faqList = document.getElementById('faq-list');
        
        earnBtn.addEventListener('click', () => {
            this.videoPlayer.open();
        });
        addLimitBtn.addEventListener('click', () => {
            this.navigation.navigateTo('quests')
        });
        cashOutBtn.addEventListener('click', () => {
            this.videoPlayer.open();
        });
        copyBtn.addEventListener('click', async () => {
        const referralLink = 'https://t.me/your_mini_app?start=ref123'; 
        try {
            await navigator.clipboard.writeText(referralLink);
            showToast('✅ Ссылка скопирована!');
        } catch (err) {
            console.error('Не удалось скопировать текст:', err);
            showToast('Ошибка копирования.');
        }
        });
        inviteBtn.addEventListener('click', () => {
            console.log('Кнопка "Пригласить" нажата. Логика перехода к шарингу.');
            showToast('Функция приглашения (заглушка).');
        });

        document.getElementById('quests-list').addEventListener('click', (e) => {
        if (e.target.classList.contains('check-btn')) {
                const button = e.target;
                const questItem = button.closest('.quest-item');
                const questId = questItem.dataset.questId;

                // Имитация проверки выполнения задания
                const isCompleted = simulateQuestCheck(questId); 

                if (isCompleted) {
                    markQuestCompleted(questItem, button);
                    showToast('🎉 Задание выполнено!');
                } else {
                    showToast('⚠️ Условия задания не выполнены.');
                }
            }
        });

        renderFaqList();

    // 2. Логика для кнопки "Чат поддержки"
    const helpChatBtn = document.querySelector('.help-chat-btn');
    helpChatBtn.addEventListener('click', () => {
        // Здесь можно открыть ссылку на чат Telegram или другую поддержку
        console.log('Кнопка "Чат поддержки" нажата. Имитация перехода.');
        // window.open('https://t.me/your_support_chat', '_blank'); 
    });

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

    
}

// ==================== INITIALIZE APP ====================
let app;

// Wait for all scripts and DOM to load
window.addEventListener('load', () => {
    app = new MiniApp();
    window.miniApp = app; // Make globally accessible for debugging
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

function simulateQuestCheck(questId) {
    // Здесь должна быть реальная логика проверки на сервере.
    // Для примера, пусть квест 1 выполняется, а квест 3 — нет.
    if (questId === 'quest1') {
        return true; 
    }
    return false;
}

// Обновление DOM при выполнении задания
function markQuestCompleted(questItem, button) {
    // 1. Добавляем класс completed к контейнеру
    questItem.classList.add('completed');
    
    // 2. Зачеркиваем заголовок
    const title = questItem.querySelector('.quest-title');
    if (title) {
        title.classList.add('completed-title');
    }

    // 3. Заменяем кнопку "Проверить" на иконку "Выполнено"
    const completedIcon = document.createElement('span');
    completedIcon.className = 'check-btn completed-icon';
    completedIcon.textContent = '✔';
    
    // Заменяем кнопку
    button.parentNode.replaceChild(completedIcon, button);
}



// ==================== FAQ ====================

function createFaqItem(title, description) {
    const item = document.createElement('div');
    item.className = 'faq-item';
    
    // Кнопка переключения (Toggle Button)
    const toggleButton = document.createElement('button');
    toggleButton.className = 'faq-toggle';
    
    toggleButton.innerHTML = `
        <span class="faq-arrow">▶</span>
        <span class="faq-title">${title}</span>
    `;

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
            const faqElement = createFaqItem(item.title, item.description);
            faqListContainer.appendChild(faqElement);
        });
    }

    // После рендеринга можно настроить обработчики событий
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




