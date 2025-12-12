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

// 1. Определяем базовую структуру квестов
const BASE_QUESTS_CONFIG = [
    {
        id: 'quest_subscribe_channel', 
        type: 'follow', 
        title: 'Подпишись на наш канал', 
        reward: '0.50', 
        link: 'https://t.me/your_channel_link'
    },
    {
        id: 'quest_casino_reg', 
        type: 'follow', 
        title: 'Регистрация в Казино', 
        reward: '1.00', 
        link: 'https://casino.com/ref'
    },
    // ... прочие квесты, которые не зависят от прогресса (MilestoneQuest)
    {
        id: 'milestone_watch_5', 
        type: 'milestone',
        title: 'Посмотри 5 видео',
        reward: '0.10',
        goal: 5 
    }
];

// Инициализация квестов на основе данных сервера
function initQuests(serverStatuses, app) { // <-- ПРИНИМАЕМ app
    const statusMap = new Map(serverStatuses.map(q => [q.quest_id, q.status]));
    const ALL_QUESTS_DATA = [];

    // [НОВОЕ] Получаем текущий счетчик просмотров
    const currentVideoCount = app.state.getCounter('videos_watched'); 

    for (const config of BASE_QUESTS_CONFIG) {
        const currentStatus = statusMap.get(config.id);
        const isCompleted = currentStatus === 'completed';
        const isVisited = currentStatus === 'visited' || isCompleted; 

        if (config.type === 'follow') {
            ALL_QUESTS_DATA.push(new FollowQuest(
                config.id, 
                config.title, 
                `+${config.reward}$`, // Награда
                config.link,          // targetLink
                isCompleted,          // isCompleted
                isVisited             // isLinkVisited
            ));
        } else if (config.type === 'milestone') {
            ALL_QUESTS_DATA.push(new MilestoneQuest(
                config.id, 
                config.title, 
                `+${config.reward}$`, 
                isCompleted, 
                // [ИЗМЕНЕНИЕ] Передаем текущий прогресс при инициализации
                config.id === 'milestone_watch_5' ? currentVideoCount : 0, 
                config.goal
            ));
        }
    }
    return ALL_QUESTS_DATA;
}

// Главная функция рендеринга
function renderQuests(ALL_QUESTS_DATA) {
    const container = document.getElementById('quests-list');
    if (!container) return;

    // 1. Очистка контейнера перед рендерингом
    container.innerHTML = ''; 

    ALL_QUESTS_DATA.forEach(quest => {
        const questItem = document.createElement('div');
        questItem.className = 'quest-item';
        questItem.dataset.id = quest.id;

        // 2. Кнопка и статус
        const button = document.createElement('button');
        button.className = 'quest-button';
        button.disabled = quest.isCompleted;

        // Определяем текст кнопки
        if (quest.isCompleted) {
            button.textContent = '✅ Выполнено';
        } else if (quest instanceof FollowQuest) {
            button.textContent = quest.isLinkVisited ? 'Проверить' : 'Перейти';
        } else if (quest instanceof MilestoneQuest) {
             // Кнопка для MilestoneQuest неактивна до выполнения
             button.textContent = quest.isCompleted ? '✅ Выполнено' : 'В процессе';
             button.disabled = true;
        } else {
             button.textContent = 'Начать';
        }
        
        // Если квест выполнен, применяем класс и отключаем кнопку
        if (quest.isCompleted) {
            markQuestCompleted(questItem, button); 
        }

        // 3. Рендеринг контента (включая прогресс-бар)
        const questContent = document.createElement('div');
        questContent.className = 'quest-content';
        questContent.innerHTML = `
            <div class="quest-info">
                <div class="quest-title">${quest.title}</div>
                <div class="quest-reward">${quest.reward}</div>
            </div>
            ${quest instanceof MilestoneQuest ? renderProgressBar(quest) : ''}
        `;
        questItem.appendChild(questContent);
        
        // 4. Добавление кнопки и элемента в контейнер
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'quest-button-container';
        buttonContainer.appendChild(button);
        
        questItem.appendChild(buttonContainer);
        container.appendChild(questItem);
    });
}

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

/**
 * Обрабатывает нажатие на кнопку "Проверить", "Перейти" или "Получить награду".
 * @param {MiniApp} app - Экземпляр главного приложения.
 */
// [ИЗМЕНЕНИЕ] Передаем ALL_QUESTS_DATA
function setupQuestHandlers(app, ALL_QUESTS_DATA) {
    const questsList = document.getElementById('quests-list');

    questsList.addEventListener('click', async (e) => {
        // ... (поиск кнопки и questId) ...

        // 1. Находим объект квеста
        const questObject = ALL_QUESTS_DATA.find(q => q.id === questId);

        // ... (проверки и отключение кнопки) ...
        
        // --- 1. FollowQuest (Подписка на канал / Казино) ---
        if (questObject instanceof FollowQuest) {
            
            // A) Состояние "Перейти" (Клик первый раз)
            if (!questObject.isLinkVisited) {
                
                // 1. Отмечаем переход на сервере (СОХРАНЯЕМ СТАТУС)
                const apiResult = await app.markQuestVisited(questId);
                
                if (apiResult.success) {
                    // 2. Открываем ссылку (как и раньше)
                    if (app.tg && app.tg.openTelegramLink) {
                        app.tg.openTelegramLink(questObject.targetLink); 
                    } else {
                        window.open(questObject.targetLink, '_blank');
                    }
                    
                    // 3. Обновляем UI/State
                    questObject.isLinkVisited = true;
                    button.textContent = 'Проверить'; 
                    app.showToast('➡️ Перейдите по ссылке, выполните и нажмите "Проверить".');
                } else {
                     app.showToast('⚠️ Ошибка сохранения статуса.', 'error');
                }
            }
            
            // B) Состояние "Проверить" (Статус 'visited' был загружен с сервера)
            else if (questObject.isLinkVisited) {
                button.textContent = '...'; // Индикатор загрузки

                // 1. Отправляем запрос на сервер для проверки (Тут все еще нужна реализация проверки на стороне бота!)
                // Для демо-целей мы пока оставим имитацию, но в реале тут должен быть API-эндпоинт
                // например: await app.checkQuestServer(questId);
                
                // *** ВРЕМЕННАЯ ИМИТАЦИЯ (нужно заменить на реальный API-вызов) ***
                const result = await app.checkQuestStatus(questId); 
                // *** КОНЕЦ ВРЕМЕННОЙ ИМИТАЦИИ ***
                
                // ... (обработка результата остается прежней) ...
                if (result.isCompleted) {
                    // ... (markQuestCompleted, updateBalance, showToast)
                } else {
                    button.textContent = 'Проверить'; 
                    app.showToast('⚠️ Условия задания не выполнены. Попробуйте снова.');
                }
            }
        
        }
        
        // ... (логика MilestoneQuest остается прежней) ...
        
        button.disabled = false;
    });
}

/**
 * Обновление DOM при выполнении задания (перенесено из app.js)
 */
// Вспомогательная функция для маркировки завершенного квеста
function markQuestCompleted(questItem, button) {
    questItem.classList.add('quest-completed');
    if (button) {
        button.textContent = '✅ Выполнено';
        button.disabled = true;
    }
}

// Новая вспомогательная функция для рендеринга прогресс-бара
function renderProgressBar(quest) {
    if (!(quest instanceof MilestoneQuest)) return '';

    const percent = Math.min(100, (quest.currentCount / quest.goal) * 100).toFixed(0);
    const progressText = `${quest.currentCount} из ${quest.goal}`;
    
    return `
        <div class="quest-progress-bar">
            <div class="progress-track">
                <div 
                    class="progress-fill ${quest.isCompleted ? 'completed-fill' : ''}" 
                    style="width: ${percent}%;">
                </div>
            </div>
            <div class="progress-text">${progressText}</div>
    `;
}

