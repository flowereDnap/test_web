// js/quests.js

// ==================== I. БАЗОВЫЙ КЛАСС КВЕСТА ====================
class Quest {
    /**
     * Базовый класс для всех заданий.
     * @param {string} id - Уникальный ID квеста.
     * @param {string} title - Заголовок задания.
     * @param {string} reward - Награда (например, "+0.50$").
     * @param {string} buttonText - Текст кнопки действия.
     * @param {boolean} isCompleted - Статус выполнения.
     */
    constructor(id, title, reward, buttonText = 'Проверить', isCompleted = false) {
        this.id = id;
        this.title = title;
        this.reward = reward;
        this.buttonText = buttonText;
        this.isCompleted = isCompleted;
    }

    /**
     * Создает HTML-элемент для отображения квеста.
     * @returns {HTMLElement}
     */
    toHtml() {
        const item = document.createElement('div');
        item.className = `quest-item ${this.isCompleted ? 'completed' : ''}`;
        item.dataset.questId = this.id;

        const titleClass = this.isCompleted ? 'quest-title completed-title' : 'quest-title';
        const buttonContent = this.isCompleted 
            ? '<span class="check-btn completed-icon">✔</span>' 
            : `<button class="check-btn primary-btn">${this.buttonText}</button>`;

        item.innerHTML = `
            <div class="quest-details">
                <h3 class="${titleClass}">${this.title}</h3>
                <p class="quest-reward">${this.reward}</p>
            </div>
            ${buttonContent}
        `;
        return item;
    }

    /**
     * Метод, который должна переопределить логика сервера.
     * @returns {boolean} - true, если квест выполнен.
     */
    async checkCompletion() {
        // Здесь должна быть логика API-запроса на сервер.
        console.warn(`Checking generic quest ID: ${this.id}. Implement API call.`);
        
        // Имитация:
        if (this.id === 'quest_subscribe_channel') {
            return true; // Пусть этот квест всегда считается выполненным для примера
        }
        return false;
    }
}

// ==================== II. НАСЛЕДУЕМЫЕ КЛАССЫ ====================

// Класс для заданий, связанных с подпиской или вступлением
class FollowQuest extends Quest {
    constructor(id, title, reward, targetLink, isCompleted = false, isLinkVisited = false) { // [ИЗМЕНЕНО] Добавлено isLinkVisited
        // Изначально кнопка всегда "Перейти", если не выполнено
        super(id, title, reward, 'Перейти', isCompleted); 
        this.targetLink = targetLink;
        this.isLinkVisited = isLinkVisited; // [НОВОЕ] Состояние для управления текстом
    }

    // [ИЗМЕНЕНО] Обновляем toHtml для управления текстом кнопки
    toHtml() {
        const item = document.createElement('div');
        item.className = `quest-item ${this.isCompleted ? 'completed' : ''}`;
        item.dataset.questId = this.id;

        const titleClass = this.isCompleted ? 'quest-title completed-title' : 'quest-title';
        
        let buttonText;
        if (this.isCompleted) {
            buttonText = 'Получено'; // Или "Получить награду", но пусть будет конечным состоянием
        } else if (this.isLinkVisited) {
            buttonText = 'Проверить'; // После перехода кнопка меняется
        } else {
            buttonText = 'Перейти'; // Изначальное состояние
        }
        
        // Кнопка, если квест не завершен
        const buttonContent = this.isCompleted 
            ? '<span class="check-btn completed-icon">✔</span>' 
            : `<button class="check-btn primary-btn">${buttonText}</button>`;

        item.innerHTML = `
            <div class="quest-details">
                <h3 class="${titleClass}">${this.title}</h3>
                <p class="quest-reward">${this.reward}</p>
            </div>
            ${buttonContent}
        `;
        return item;
    }
    
    // Удаляем checkCompletion из FollowQuest, так как логика теперь будет в обработчике.
    // Если его оставить, он должен быть пустым или вызывать API.
}


// Класс для заданий, связанных с достижением определенного количества действий
class MilestoneQuest extends Quest {
    constructor(id, title, reward, requiredCount, currentCount, isCompleted = false) {
        super(id, title, reward, 'Получить награду', isCompleted);
        this.requiredCount = requiredCount;
        this.currentCount = currentCount;
    }
    
    toHtml() {
        const htmlItem = super.toHtml();
        // Добавляем индикатор прогресса (если квест не завершен)
        if (!this.isCompleted) {
            const progress = document.createElement('span');
            progress.className = 'quest-progress';
            progress.textContent = ` (${this.currentCount}/${this.requiredCount})`;
            htmlItem.querySelector('.quest-title').appendChild(progress);
        }
        return htmlItem;
    }
}

// ==================== III. ДАННЫЕ И РЕНДЕРИНГ ====================

// Массив с данными, который в будущем будет загружаться с сервера
const ALL_QUESTS_DATA = [
     new FollowQuest(
        'quest_subscribe_channel', 
        'Подпишись на наш канал', 
        '+0.50$', 
        'https://t.me/your_channel_link'
    ),
    new MilestoneQuest(
        'quest_view_10', 
        'Посмотреть 10 видео', 
        '+0.20$', 
        10, 
        5 // Предположим, пользователь посмотрел 5
    ),
    new MilestoneQuest(
        'quest_view_100', 
        'Посмотреть 100 видео', 
        '+2.00$', 
        100, 
        5, 
        false // Не завершен
    ),
];


/**
 * Рендерит список квестов в DOM.
 * @param {Array<Quest>} questsArray - Массив объектов Quest.
 */
function renderQuestList(questsArray) {
    const questsListContainer = document.getElementById('quests-list');
    if (!questsListContainer) return;

    questsListContainer.innerHTML = ''; // Очищаем статический контент

    questsArray.forEach(quest => {
        questsListContainer.appendChild(quest.toHtml());
    });
}

// ==================== IV. ЛОГИКА ОБРАБОТКИ СОБЫТИЙ ====================

// Файл js/quests.js, секция IV. ЛОГИКА ОБРАБОТКИ СОБЫТИЙ

/**
 * Обрабатывает нажатие на кнопку "Проверить", "Перейти" или "Получить награду".
 * @param {MiniApp} app - Экземпляр главного приложения.
 */
function setupQuestHandlers(app) {
    const questsList = document.getElementById('quests-list');

    questsList.addEventListener('click', async (e) => {
        const button = e.target.closest('.check-btn.primary-btn');
        if (!button) return;

        const questItem = button.closest('.quest-item');
        const questId = questItem.dataset.questId;
        const questObject = ALL_QUESTS_DATA.find(q => q.id === questId);

        if (!questObject || questObject.isCompleted) return;
        
        button.disabled = true;
        
        // --- 1. FollowQuest (Подписка на канал) ---
        if (questObject instanceof FollowQuest) {
            
            // A) Состояние "Перейти" (Клик первый раз)
            if (!questObject.isLinkVisited) {
                
                // 1. Открываем ссылку
                if (app.tg && app.tg.openTelegramLink) {
                    app.tg.openTelegramLink(questObject.targetLink); 
                } else {
                    // Fallback для десктопа или старых версий
                    window.open(questObject.targetLink, '_blank');
                }
                
                // 2. Меняем состояние и текст кнопки на "Проверить"
                questObject.isLinkVisited = true;
                button.textContent = 'Проверить'; 
                button.disabled = false;
                app.showToast('➡️ Перейдите по ссылке, подпишитесь и нажмите "Проверить".');
                return;
            }
            
            // B) Состояние "Проверить" (Клик после перехода)
            if (questObject.isLinkVisited) {
                button.textContent = '...'; // Индикатор загрузки

                // 1. Отправляем запрос на сервер для проверки подписки (API-запрос)
                const result = await app.checkQuestStatus(questId);
                
                // 2. Проверяем результат
                if (result.isCompleted) {
                    // Успех: Начисляем награду
                    questObject.isCompleted = true; 
                    markQuestCompleted(questItem, button); 
                    app.state.updateBalance(result.reward); 
                    app.updateUI(); 
                    app.showToast(`🎉 Задание выполнено! Награда: +${result.reward}$`);
                    
                } else {
                    // Провал: Возвращаем в исходное состояние
                    questObject.isLinkVisited = false; // Сбрасываем состояние
                    button.textContent = 'Перейти'; // Возвращаем исходный текст
                    app.showToast('⚠️ Подписка не найдена. Попробуйте снова.');
                }
            }
        
        // --- 2. Generic Quest / Milestone Quest (Прочие квесты) ---
        } else {
            // ... (Старая логика проверки для MilestoneQuest или других квестов) ...
            
            button.textContent = '...'; 
            const result = await app.checkQuestStatus(questId);
            
            if (result.isCompleted) {
                questObject.isCompleted = true; 
                markQuestCompleted(questItem, button); 
                app.state.updateBalance(result.reward);
                app.updateUI();
                app.showToast(`🎉 Задание выполнено! Награда: +${result.reward}$`);
            } else {
                app.showToast('⚠️ Условия задания пока не выполнены.');
            }
        }
        
        button.disabled = false;
    });
}

/**
 * Обновление DOM при выполнении задания (перенесено из app.js)
 */
function markQuestCompleted(questItem, button) {
    questItem.classList.add('completed');
    const title = questItem.querySelector('.quest-title');
    if (title) {
        title.classList.add('completed-title');
    }
    
    // Заменяем кнопку на иконку "Выполнено"
    const completedIcon = document.createElement('span');
    completedIcon.className = 'check-btn completed-icon';
    completedIcon.textContent = '✔';
    
    // Заменяем кнопку
    button.parentNode.replaceChild(completedIcon, button);
}

// Глобальный запуск рендеринга
renderQuestList(ALL_QUESTS_DATA);