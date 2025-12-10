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
    constructor(id, title, reward, targetLink, isCompleted = false) {
        super(id, title, reward, 'Перейти', isCompleted);
        this.targetLink = targetLink;
    }

    // Переопределяем метод для открытия ссылки перед проверкой
    async checkCompletion() {
        if (!this.isCompleted) {
             // Открываем ссылку, чтобы пользователь мог выполнить действие
            window.open(this.targetLink, '_blank');
        }
        
        // Тут будет API запрос: return await api.checkFollow(this.id);
        return await super.checkCompletion(); // Временно используем базовый check
    }
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

    async checkCompletion() {
        // Здесь будет API запрос: return this.currentCount >= this.requiredCount;
        return this.isCompleted; 
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
    new Quest(
        'quest_share_app', 
        'Поделиться приложением', 
        '+0.10$', 
        'Поделиться'
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

/**
 * Обрабатывает нажатие на кнопку "Проверить" или "Получить награду".
 * @param {MiniApp} app - Экземпляр главного приложения.
 */
function setupQuestHandlers(app) {
    const questsList = document.getElementById('quests-list');

    questsList.addEventListener('click', async (e) => {
        const button = e.target.closest('.check-btn.primary-btn');
        if (!button) return;

        const questItem = button.closest('.quest-item');
        const questId = questItem.dataset.questId;

        // Находим объект квеста по ID
        const questObject = ALL_QUESTS_DATA.find(q => q.id === questId);

        if (!questObject || questObject.isCompleted) {
            return; // Квест уже завершен или не найден
        }
        
        button.textContent = '...'; // Индикатор загрузки

        // Выполняем проверку через метод класса
        const isCompleted = await questObject.checkCompletion();

        button.textContent = questObject.buttonText; // Восстанавливаем текст

        if (isCompleted) {
            // В реальном приложении это должно прийти с сервера, 
            // но для UI-обновления:
            questObject.isCompleted = true; 
            
            // Обновляем внешний вид элемента
            markQuestCompleted(questItem, button); 
            
            // Здесь должна быть логика начисления награды через API
            app.showToast('🎉 Задание выполнено! Награда начислена.');
            // app.state.updateBalance(questObject.reward);
        } else {
            app.showToast('⚠️ Условия задания не выполнены.');
        }
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