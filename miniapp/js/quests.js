// ==================== I. БАЗОВЫЙ КЛАСС КВЕСТА ====================
class Quest {
    constructor(id, title, reward, isCompleted = false) {
        this.id = id;
        this.title = title;
        this.reward = reward;
        this.isCompleted = isCompleted;
    }

    vibrate(type = 'success') {
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred(type);
        }
    }

    /** Безопасное создание HTML карточки задания */
    toHtml() {
        const item = document.createElement('div');
        item.className = `quest-item ${this.isCompleted ? 'completed' : ''}`;
        item.dataset.id = this.id;

        const details = document.createElement('div');
        details.className = 'quest-details';

        const titleEl = document.createElement('h3');
        titleEl.className = `quest-title ${this.isCompleted ? 'completed-title' : ''}`;
        titleEl.textContent = this.title;

        const rewardEl = document.createElement('p');
        rewardEl.className = 'quest-reward';
        rewardEl.textContent = this.reward;

        details.appendChild(titleEl);
        details.appendChild(rewardEl);

        const btn = document.createElement('button');
        btn.className = 'check-btn primary-btn quest-button';
        this.updateButtonUI(btn);

        item.appendChild(details);
        item.appendChild(btn);
        
        return item;
    }

    updateButtonUI(btn) {
        if (this.isCompleted) {
            btn.textContent = '✅';
            btn.disabled = true;
            btn.classList.add('completed-icon');
        }
    }
}

// ==================== II. НАСЛЕДУЕМЫЕ КЛАССЫ ====================

class FollowQuest extends Quest {
    constructor(id, title, reward, targetLink, isCompleted, isLinkVisited) {
        super(id, title, reward, isCompleted);
        this.targetLink = targetLink;
        this.isLinkVisited = isLinkVisited;
    }

    updateButtonUI(btn) {
        super.updateButtonUI(btn);
        if (!this.isCompleted) {
            btn.textContent = this.isLinkVisited ? 'Проверить' : 'Перейти';
            btn.disabled = false;
        }
    }

    async onClick(app, btn) {
        if (!this.isLinkVisited) {
            // Этап 1: Фиксация перехода
            const res = await app.markQuestVisited(this.id);
            if (res.success || res.status === 'ok') {
                this.isLinkVisited = true;
                this.updateButtonUI(btn);
                // Открываем ссылку
                if (window.Telegram?.WebApp?.openTelegramLink) {
                    app.tg.openTelegramLink(this.targetLink);
                } else {
                    window.open(this.targetLink, '_blank');
                }
            }
            btn.disabled = false; // Возвращаем кнопку в строй
        } else {
            // Этап 2: Унифицированная проверка
            btn.textContent = '...';
            const apiResult = await app.verifyQuest(this.id);
            
            if (apiResult.isCompleted) {
                this.isCompleted = true;
                this.vibrate();
                this.updateButtonUI(btn);
                app.state.addToBalance(apiResult.reward);
                app.showToast('Задание выполнено!', 'success');
                app.updateUI();
            } else {
                app.showToast('Подписка не подтверждена', 'error');
                
                this.isLinkVisited = false; 
                
                this.updateButtonUI(btn);
                btn.disabled = false;
            }
        }
    }
}

class MilestoneQuest extends Quest {
    constructor(id, title, reward, requiredCount, currentCount, isCompleted) {
        super(id, title, reward, isCompleted);
        this.requiredCount = requiredCount;
        this.currentCount = currentCount;
    }

    toHtml() {
        const item = super.toHtml();
        const details = item.querySelector('.quest-details');
        details.appendChild(this._renderProgressBar());
        return item;
    }

    updateButtonUI(btn) {
        super.updateButtonUI(btn);
        if (!this.isCompleted) {
            const canClaim = this.currentCount >= this.requiredCount;
            btn.textContent = canClaim ? 'Забрать' : `${this.currentCount}/${this.requiredCount}`;
            btn.disabled = !canClaim;
        }
    }

    async onClick(app, btn) {
        btn.textContent = '...';
        // Используем тот же универсальный метод
        const apiResult = await app.verifyQuest(this.id);
        
        if (apiResult.isCompleted) {
            this.isCompleted = true;
            this.vibrate();
            this.updateButtonUI(btn);
            app.state.addToBalance(apiResult.reward);
            app.showToast('Награда получена!', 'success');
            app.updateUI();
        } else {
            app.showToast('Условие еще не выполнено', 'error');
            this.updateButtonUI(btn);
            btn.disabled = (this.currentCount < this.requiredCount);
        }
    }

    _renderProgressBar() {
        const percent = Math.min(100, (this.currentCount / this.requiredCount) * 100);
        const container = document.createElement('div');
        container.className = 'quest-progress-bar';

        const track = document.createElement('div');
        track.className = 'progress-track';
        
        const fill = document.createElement('div');
        // ДОБАВЛЯЕМ КЛАСС completed-fill, если счетчик заполнен
        fill.className = `progress-fill ${percent >= 100 ? 'completed-fill' : ''}`;
        fill.style.width = `${percent}%`;

        const text = document.createElement('div');
        text.className = 'progress-text';
        text.textContent = `${this.currentCount} из ${this.requiredCount}`;

        track.appendChild(fill);
        container.appendChild(track);
        container.appendChild(text);
        return container;
    }
}



class CpaQuest extends Quest {
    constructor(id, title, reward, isCompleted, isVisited) {
        super(id, title, reward || 'Бонус', isCompleted);
        this.isVisited = isVisited;
        this.cachedLink = null; // Здесь сохраним ссылку, чтобы не дергать API лишний раз
    }

    updateButtonUI(btn) {
        super.updateButtonUI(btn);
        if (!this.isCompleted) {
            // Кнопка ВСЕГДА активна, пока квест не выполнен
            btn.textContent = this.isVisited ? 'Продолжить' : 'Начать';
            btn.disabled = false; 
            
            // Визуально подсветим, что юзер уже в процессе (опционально)
            if (this.isVisited) {
                btn.classList.add('in-progress');
            }
        }
    }

    async onClick(app, btn) {
        // Если ссылка уже есть в памяти — просто открываем
        if (this.cachedLink) {
            window.Telegram.WebApp.openLink(this.cachedLink);
            return;
        }

        btn.textContent = '...';
        try {
            const response = await fetch('/api/quest/generate_cpa_link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    telegram_id: app.state.user.id,
                    quest_id: this.id
                })
            });
            
            const data = await response.json();
            
            if (data.link) {
                this.isVisited = true;
                this.cachedLink = data.link; // Кешируем ссылку
                this.updateButtonUI(btn);
                window.Telegram.WebApp.openLink(data.link);
            } else {
                app.showToast('Ошибка. Попробуйте позже', 'error');
                this.updateButtonUI(btn);
            }
        } catch (e) {
            app.showToast('Ошибка сети', 'error');
            this.updateButtonUI(btn);
        }
    }
}

// ==================== III. ЛОГИКА ИНИЦИАЛИЗАЦИИ ====================

async function initQuests(serverStatuses, app) {
    // 1. Получаем основной конфиг квестов с сервера
    let QUEST_CONFIG = [];
    try {
        const response = await fetch('/api/quest/get_list');
        QUEST_CONFIG = await response.json();
    } catch (e) {
        console.error("Failed to load quest config:", e);
        return [];
    }

    // 2. Превращаем статусы из БД в карту
    const statuses = Array.isArray(serverStatuses) ? serverStatuses : [];
    const statusMap = new Map(statuses.map(q => [String(q.quest_id), q.status]));
    
    // Получаем текущее число просмотров для Milestone квестов
    const currentVideoCount = app.state.getCounter('videos_watched');
    

    // 3. Создаем объекты нужных классов
    return QUEST_CONFIG.map(config => {
        const status = statusMap.get(String(config.id));
        const isCompleted = (status === 'completed');
        const isVisited = (status === 'visited' || isCompleted);

        if (config.type === 'follow') {
            return new FollowQuest(
                config.id, 
                config.title, 
                `+$${config.reward}`, 
                config.link, 
                isCompleted, 
                isVisited
            );
        } else if (config.type === 'milestone') {
            return new MilestoneQuest(
                config.id, 
                config.title, 
                `+$${config.reward}`, 
                config.goal, 
                currentVideoCount, 
                isCompleted
            );
        } else if (config.type === 'cpa') {
            return new CpaQuest(
                config.id,
                config.title,
                config.reward > 0 ? `+$${config.reward}` : 'Бонус %',
                isCompleted,
                isVisited
            );
        }
        return null;
    }).filter(q => q !== null);
}

/** Рендеринг списка квестов в DOM */
function renderQuestList(questsArray) {
    const container = document.getElementById('quests-list');
    if (!container) return;

    container.innerHTML = ''; // Очистка (безопасно, так как мы тут же наполняем элементами)

    if (questsArray.length === 0) {
        container.textContent = 'Доступных заданий пока нет.';
        return;
    }

    questsArray.forEach(quest => {
        container.appendChild(quest.toHtml());
    });
}

/** Глобальный обработчик кликов */
function setupQuestHandlers(app, ALL_QUESTS_DATA) {
    const list = document.getElementById('quests-list');
    if (!list) return;

    // ПРАВКА: Удаляем старые слушатели, если они были (через замену элемента или проверку)
    // Но так как мы используем делегирование на контейнер, достаточно одного раза.
    // Если контейнер перерисовывается полностью, старые слушатели на кнопках пропадут сами.
    
    list.onclick = async (e) => {
        const btn = e.target.closest('.quest-button');
        if (!btn || btn.disabled) return;

        const item = btn.closest('.quest-item');
        const questId = item.dataset.id;
        const questObject = ALL_QUESTS_DATA.find(q => q.id === questId);

        if (questObject && !questObject.isCompleted) {
            btn.disabled = true; // Блокируем от двойного клика
            await questObject.onClick(app, btn);
        }
    };
}