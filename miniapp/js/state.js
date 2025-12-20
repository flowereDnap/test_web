// ==================== APP STATE ====================
class AppState {
    constructor() {
        // Оставляем значения по умолчанию для красоты до момента загрузки
        this.balance = 0.00;
        this.todayCount = 0;
        this.totalEarned = 0.00;
        this.maxCount = 10;
        this.counters = {};
    }

    // НОВЫЙ МЕТОД: Загрузка данных с твоего бэкенда
    async loadState(userId) {
        try {
            // Используем эндпоинт, который мы прописали в боте (/api/quest/statuses возвращает и баланс, и счетчики)
            const response = await fetch(`/api/quest/statuses?telegram_id=${userId}`);
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.balance = parseFloat(data.balance) || 0;
                this.counters = data.counters || {};
                // Если в будущем бэк будет отдавать лимиты:
                // this.todayCount = data.today_count;
                return true;
            }
        } catch (e) {
            console.error("AppState: Ошибка загрузки с сервера, берем из кеша", e);
            // Если сервер лег, можно попробовать подтянуть из localStorage
            this.balance = parseFloat(localStorage.getItem('balance') || '0');
        }
        return false;
    }

    updateBalance(amount) {
        this.balance = parseFloat(this.balance) + parseFloat(amount);
        this.save();
    }

    setCounters(counters) {
        this.counters = counters; 
    }
    
    getCounter(key) {
        return this.counters[key] || 0;
    }

    save() {
        localStorage.setItem('balance', this.balance.toFixed(2));
    }

    getBalance() {
        // Возвращаем число, чтобы toFixed(2) в app.js не падал
        return parseFloat(this.balance);
    }

    // Исправленный метод
    setBalance(newBalance) {
        this.balance = parseFloat(newBalance) || 0.00;
        this.save();
    }

    getTodayCount() { return this.todayCount; }
    getMaxCount() { return this.maxCount; }
    getTotalEarned() { return '$' + this.totalEarned.toFixed(2); }
}