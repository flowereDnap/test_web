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
        this.applyTelegramTheme();
        
        // Detect user language
        this.detectLanguage();
        
        // Apply translations
        applyTranslations(this.currentLang);
        
        // Initialize earn button
        this.initEarnButton();
        
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

    initEarnButton() {
        const earnBtn = document.getElementById('earn-btn');
        earnBtn.addEventListener('click', () => {
            this.videoPlayer.open();
        });
    }

    updateUI() {
        document.getElementById('balance-value').textContent = this.state.getBalance();
        document.getElementById('today-count').textContent = this.state.getTodayCount();
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
