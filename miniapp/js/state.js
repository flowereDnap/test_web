// ==================== APP STATE ====================
class AppState {
    constructor() {
        this.balance = parseFloat(localStorage.getItem('balance') || '12.45');
        this.todayCount = parseInt(localStorage.getItem('todayCount') || '1');
        this.totalEarned = parseFloat(localStorage.getItem('totalEarned') || '145.20');
        this.maxCount = parseInt(localStorage.getItem('maxCount') || '10');
        this.counters = {};
    }

    updateBalance(amount) {
        this.balance += amount;
        this.todayCount += 1;
        this.totalEarned += amount;
        this.save();
    }

    setCounters(counters) {
        this.counters = counters; // Сохраняем все счетчики
    }
    
    getCounter(key) {
        return this.counters[key] || 0;
    }

    save() {
        localStorage.setItem('balance', this.balance.toFixed(2));
        localStorage.setItem('todayCount', this.todayCount.toString());
        localStorage.setItem('totalEarned', this.totalEarned.toFixed(2));
        localStorage.setItem('maxCount', this.maxCount.toString());
    }

    getBalance() {
        return this.balance.toFixed(2);
    }

    setBalance(newBalance) {
        this._balance = parseFloat(newBalance) || 0.00;
    }

    getTodayCount() {
        return this.todayCount;
    }

    getMaxCount() {
        return this.maxCount;
    }

    getTotalEarned() {
        return '$' + this.totalEarned.toFixed(2);
    }
}
