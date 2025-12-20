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

    vibrate(type = 'success') {
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred(type);
        }
    }

    /**
     * Создает HTML-элемент для отображения квеста.
     * @returns {HTMLElement}
     */
    /**
 * Создает HTML-элемент для отображения квеста, используя безопасный DOM API.
 * @returns {HTMLElement}
 */
    toHtml() {
        // 1. Создаем основной элемент
        const item = document.createElement('div');
        item.className = `quest-item ${this.isCompleted ? 'completed' : ''}`;
        item.dataset.questId = this.id;

        // 2. Создаем контейнер деталей (quest-details)
        const details = document.createElement('div');
        details.className = 'quest-details';

        // 3. Создаем заголовок (h3)
        const titleElement = document.createElement('h3');
        const titleClass = this.isCompleted ? 'quest-title completed-title' : 'quest-title';
        titleElement.className = titleClass;
        titleElement.textContent = this.title;

        // 4. Создаем награду (p)
        const rewardElement = document.createElement('p');
        rewardElement.className = 'quest-reward';
        rewardElement.textContent = this.reward;
        
        // Сборка деталей
        details.appendChild(titleElement);
        details.appendChild(rewardElement);
        item.appendChild(details);

        // 5. Создаем кнопку или иконку выполнения
        let actionElement;
        
        if (this.isCompleted) {
            // Если выполнено, создаем <span> с галочкой
            actionElement = document.createElement('span');
            actionElement.className = 'check-btn completed-icon';
            actionElement.textContent = '✔';
        } else {
            // Если не выполнено, создаем <button>
            actionElement = document.createElement('button');
            actionElement.className = 'check-btn primary-btn';
            actionElement.textContent = this.buttonText;
            actionElement.disabled = this.isCompleted;
        }

        // 6. Добавляем элемент действия в основной элемент
        item.appendChild(actionElement);

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

    updateButton(btn) {
        if (this.isCompleted) {
            btn.textContent = '✅';
            btn.disabled = true;
        } else {
            btn.textContent = this.isVisited ? 'Проверить' : 'Перейти';
        }
    }

    // [ИЗМЕНЕНО] Обновляем toHtml для управления текстом кнопки
    toHtml() {
        const item = document.createElement('div');
        item.className = `quest-item ${this.isCompleted ? 'completed' : ''}`;
        item.dataset.questId = this.id;

        const details = document.createElement('div');
        details.className = 'quest-details';

        const titleElement = document.createElement('h3');
        titleElement.className = this.isCompleted ? 'quest-title completed-title' : 'quest-title';
        titleElement.textContent = this.title;

        const rewardElement = document.createElement('p');
        rewardElement.className = 'quest-reward';
        rewardElement.textContent = this.reward;
        
        details.appendChild(titleElement);
        details.appendChild(rewardElement);
        item.appendChild(details);

        // --- Логика КНОПКИ ---
        let buttonContentElement;
        
        if (this.isCompleted) {
            buttonContentElement = document.createElement('span');
            buttonContentElement.className = 'check-btn completed-icon';
            buttonContentElement.textContent = '✔';
        } else {
            let buttonText;
            if (this.isLinkVisited) {
                buttonText = 'Проверить'; // После перехода кнопка меняется
            } else {
                buttonText = 'Перейти'; // Изначальное состояние
            }
            
            buttonContentElement = document.createElement('button');
            buttonContentElement.className = 'check-btn primary-btn';
            buttonContentElement.textContent = buttonText;
        }

        item.appendChild(buttonContentElement);
        return item;
    }

    async onClick(app, btn) {
        const userId = app.tg.initDataUnsafe?.user?.id;
        
        if (!this.isVisited) {
            // Шаг 1: Помечаем визит
            await fetch('/api/quest/visited', {
                method: 'POST',
                body: JSON.stringify({ quest_id: this.id, telegram_id: userId })
            });
            window.Telegram.WebApp.openTelegramLink(this.targetLink);
            this.isVisited = true;
            this.updateButton(btn);
        } else {
            // Шаг 2: Проверяем выполнение
            const res = await fetch('/api/quest/verify', {
                method: 'POST',
                body: JSON.stringify({ quest_id: this.id, telegram_id: userId })
            }).then(r => r.json());

            if (res.isCompleted) {
                this.isCompleted = true;
                this.vibrate();
                this.updateButton(btn);
                app.state.updateBalance(res.reward);
            }
        }
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
        // 1. Используем базовый рендеринг
        const htmlItem = super.toHtml();
        
        // 2. Добавляем индикатор прогресса (если квест не завершен)
        if (!this.isCompleted) {
            const progress = document.createElement('span');
            progress.className = 'quest-progress';
            progress.textContent = ` (${this.currentCount}/${this.requiredCount})`;
            
            // Находим h3 внутри quest-details
            const titleElement = htmlItem.querySelector('.quest-details h3'); 
            
            if (titleElement) {
                // Добавляем текст прогресса рядом с заголовком
                titleElement.appendChild(progress);
                
                // Создаем и добавляем сам прогресс-бар
                const progressBarElement = this._renderProgressBar(); // Вызываем внутренний метод
                htmlItem.querySelector('.quest-details').appendChild(progressBarElement);
            }
        }

        if (!this.isCompleted) {
            const canClaim = this.currentCount >= this.requiredCount;
            actionElement.textContent = canClaim ? 'Получить награду' : 'В процессе';
            actionElement.disabled = !canClaim;
            if (canClaim) actionElement.classList.add('pulse-animation'); // Доп. акцент
        }

        return htmlItem;
    }

    /**
     * Вспомогательный метод для рендеринга прогресс-бара
     */
    _renderProgressBar() {
        const percent = Math.min(100, (this.currentCount / this.requiredCount) * 100).toFixed(0);
        const progressText = `${this.currentCount} из ${this.requiredCount}`;

        const progressBarContainer = document.createElement('div');
        progressBarContainer.className = 'quest-progress-bar';

        const track = document.createElement('div');
        track.className = 'progress-track';

        const fill = document.createElement('div');
        fill.className = `progress-fill ${this.isCompleted ? 'completed-fill' : ''}`;
        fill.style.width = `${percent}%`;

        const text = document.createElement('div');
        text.className = 'progress-text';
        text.textContent = progressText;

        track.appendChild(fill);
        progressBarContainer.appendChild(track);
        progressBarContainer.appendChild(text);

        return progressBarContainer;
    }
}

// ==================== III. ДАННЫЕ И РЕНДЕРИНГ ====================



// Инициализация квестов на основе данных сервера
async function initQuests(serverStatuses, app) { // <-- ПРИНИМАЕМ app
    // ПРОВЕРКА: Убедимся, что serverStatuses является массивом, иначе .map упадет
    const statuses = Array.isArray(serverStatuses) ? serverStatuses : [];
    const statusMap = new Map(statuses.map(q => [q.quest_id, q.status]));
    const ALL_QUESTS_DATA = [];

    // [НОВОЕ] Получаем текущий счетчик просмотровнам
    const currentVideoCount = app.state.getCounter('videos_watched'); 

    let BASE_QUESTS_CONFIG = [];
    try {
        const response = await fetch('/api/quest/get_list');
        if (!response.ok) {
            throw new Error(`Failed to fetch quest config: ${response.status}`);
        }
        BASE_QUESTS_CONFIG = await response.json();
    } catch (e) {
        console.error("Error loading quest configuration:", e);
        app.showToast('⚠️ Ошибка загрузки списка заданий.', 'error');
        return ALL_QUESTS_DATA;
    }

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
                config.goal, // ❗ ИСПРАВЛЕНИЕ: requiredCount теперь config.goal
                config.id === 'milestone_watch_5' ? currentVideoCount : 0, // currentCount
                isCompleted // ❗ ИСПРАВЛЕНИЕ: isCompleted в конце
            ));
        }
    }
    return ALL_QUESTS_DATA;
}


/**
 * Рендерит список квестов в DOM.
 * @param {Array<Quest>} questsArray - Массив объектов Quest.
 */
function renderQuestList(questsArray) {
    const questsListContainer = document.getElementById('quests-list');
    if (!questsListContainer) return;
    
    // ❗ ИСПРАВЛЕНИЕ: Проверка на массив
    if (!Array.isArray(questsArray)) {
        console.error("renderQuestList received non-array data. Check if await is used in app.js.", questsArray);
        return; 
    }

    questsListContainer.innerHTML = ''; // Очищаем

    questsArray.forEach(quest => {
        questsListContainer.appendChild(quest.toHtml());
    });
}

// ==================== IV. ЛОГИКА ОБРАБОТКИ СОБЫТИЙ ====================

/**
 * Обрабатывает нажатие на кнопку "Проверить", "Перейти" или "Получить награду".
 * @param {MiniApp} app - Экземпляр главного приложения.
 * @param {Array<Quest>} ALL_QUESTS_DATA - Массив объектов Quest.
 */
function setupQuestHandlers(app, ALL_QUESTS_DATA) {
    const questsList = document.getElementById('quests-list');
    
    // ❗ ИСПРАВЛЕНИЕ: Проверка на массив в обработчике
    if (!Array.isArray(ALL_QUESTS_DATA)) {
        console.warn("setupQuestHandlers received non-array data. Cannot set up handlers.");
        return;
    }


    questsList.addEventListener('click', async (e) => {
        
        // 1. Находим кнопку, на которую кликнули
        const button = e.target.closest('.quest-button');
        if (!button) return; 

        // 2. Находим родительский элемент квеста
        const questItem = e.target.closest('.quest-item');
        if (!questItem) return; 
        
        // 3. Получаем questId из data-атрибута (ИСПРАВЛЕНИЕ ReferenceError)
        const questId = questItem.dataset.id || questItem.dataset.questId; // Проверяем оба варианта
        if (!questId) return;

        // 4. Находим объект квеста
        const questObject = ALL_QUESTS_DATA.find(q => q.id === questId); 

        // Дополнительная проверка, если квест уже выполнен или объект не найден
        if (!questObject || questObject.isCompleted) {
            return; 
        }

        // Отключаем кнопку на время обработки
        button.disabled = true;

        let apiResult = { isCompleted: false, reward: 0 };
        
        // --- 1. FollowQuest (Подписка на канал / Казино) ---
        if (questObject instanceof FollowQuest) {
            
            // A) Состояние "Перейти" (Клик первый раз)
            if (!questObject.isLinkVisited) {
                
                // 1. Отмечаем переход на сервере (СОХРАНЯЕМ СТАТУС 'visited')
                const visitResult = await app.markQuestVisited(questId);
                
                if (visitResult.success) {
                    // 2. Открываем ссылку
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
                    app.showToast('⚠️ Ошибка сохранения статуса перехода.', 'error');
                }
                
                button.disabled = false; // Включаем кнопку снова после обработки "Перейти"
                return;
            }
            
            // B) Состояние "Проверить" (Статус 'visited')
            else if (questObject.isLinkVisited) {
                button.textContent = '...'; // Индикатор загрузки

                // Отправляем запрос на сервер для проверки выполнения
                apiResult = await app.checkQuestStatus(questId); 
            }
        
        } 
        
        // --- 2. MilestoneQuest (Достижение цели) ---
        else if (questObject instanceof MilestoneQuest) {
            // Кнопка MilestoneQuest должна быть активна только если currentCount >= requiredCount
            if (questObject.currentCount >= questObject.requiredCount && !questObject.isCompleted) {
                button.textContent = '...'; // Индикатор загрузки
                
                // Отправляем запрос на сервер для завершения и получения награды
                apiResult = await app.completeQuest(questId); // Предполагаем, что этот метод существует
            } else {
                // Если не достигнута цель, кнопка должна быть неактивна и не должна обрабатываться
                button.disabled = false; 
                return;
            }
        }
        
        // --- ОБЩАЯ ЛОГИКА ЗАВЕРШЕНИЯ КВЕСТА ---
        
        if (apiResult.isCompleted) {
            if (window.Telegram?.WebApp?.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
            }

            // 1. Обновляем объект квеста
            questObject.isCompleted = true;
            
            // 2. Обновляем UI
            // Используем вспомогательную функцию для обновления DOM
            markQuestCompleted(questItem, button); // Предполагаем, что этот метод существует в MiniApp/quests.js
            
            // 3. Обновляем баланс
            if (apiResult.reward) {
                app.state.updateBalance(apiResult.reward); // Используем updateBalance из state.js
            } else {
                // Если награда не пришла с сервера, используем награду из объекта квеста (для FollowQuest)
                const rewardAmount = parseFloat(questObject.reward.replace('+', '').replace('$', '')) || 0;
                app.state.updateBalance(rewardAmount); 
            }
            
            // 4. Показываем сообщение
            app.showToast(`🎉 Квест "${questObject.title}" выполнен! Получено ${questObject.reward}.`, 'success');

        } else if (questObject instanceof FollowQuest && questObject.isLinkVisited) {

            // Если FollowQuest проверялся, но не выполнен, возвращаем кнопку в состояние "Перейти"
            questObject.isLinkVisited = false;
            
            button.textContent = 'Перейти';
            app.showToast('⚠️ Условия задания не выполнены. Попробуйте снова.', 'error');
            
        } else if (questObject instanceof MilestoneQuest) {
             // Если MilestoneQuest проверялся, но сервер отказал
             button.textContent = 'Получить награду';
             app.showToast('⚠️ Ошибка при получении награды.', 'error');
        }

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
    if (!(quest instanceof MilestoneQuest)) return null; // Возвращаем null вместо пустой строки

    const percent = Math.min(100, (quest.currentCount / quest.requiredCount) * 100).toFixed(0);
    const progressText = `${quest.currentCount} из ${quest.requiredCount}`;

    const progressBarContainer = document.createElement('div');
    progressBarContainer.className = 'quest-progress-bar';

    const track = document.createElement('div');
    track.className = 'progress-track';

    const fill = document.createElement('div');
    fill.className = `progress-fill ${quest.isCompleted ? 'completed-fill' : ''}`;
    fill.style.width = `${percent}%`;

    const text = document.createElement('div');
    text.className = 'progress-text';
    text.textContent = progressText;

    track.appendChild(fill);
    progressBarContainer.appendChild(track);
    progressBarContainer.appendChild(text);

    return progressBarContainer; // Возвращаем элемент
}