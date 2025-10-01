// ==================== NAVIGATION ====================
class Navigation {
    constructor(app) {
        this.app = app;
        this.currentPage = 'cash';
        this.init();
    }

    init() {
        const navButtons = document.querySelectorAll('.nav-btn');

        navButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetPage = button.dataset.page;
                this.navigateTo(targetPage);
                
                // Haptic feedback
                if (CONFIG.hapticFeedback && this.app.tg.HapticFeedback) {
                    this.app.tg.HapticFeedback.impactOccurred('light');
                }
            });
        });
    }

    navigateTo(pageId) {
        const navButtons = document.querySelectorAll('.nav-btn');
        const pages = document.querySelectorAll('.page');
        
        // Remove active class
        navButtons.forEach(btn => btn.classList.remove('active'));
        pages.forEach(page => page.classList.remove('active'));
        
        // Add active class
        const targetButton = document.querySelector(`[data-page="${pageId}"]`);
        const targetPage = document.getElementById(pageId);
        
        if (targetButton && targetPage) {
            targetButton.classList.add('active');
            targetPage.classList.add('active');
            this.currentPage = pageId;
        }
    }
}
