// ==================== VIDEO PLAYER ====================
class VideoPlayer {
    constructor(app) {
        this.app = app;
        this.overlay = document.getElementById('video-overlay');
        this.video = document.getElementById('video-player');
        this.closeBtn = document.getElementById('video-close');
        this.progressBar = document.getElementById('progress-bar');
        this.canSkip = false;
        this.watchedPercentage = 0;
        this.currentVideo = null;

        this.init();
    }

    init() {
        this.video.addEventListener('timeupdate', () => this.onProgress());
        this.video.addEventListener('ended', () => this.onVideoEnd());
        this.closeBtn.addEventListener('click', () => this.close());

        this.video.addEventListener('seeking', () => {
            if (this.video.currentTime > (this.video.dataset.maxTime || 0)) {
                this.video.currentTime = this.video.dataset.maxTime || 0;
            }
        });
    }

    async loadRandomVideo() {
        try {
            const backend = window.location.origin; // same origin
            const initData = window.Telegram.WebApp.initData;
            const res = await fetch(`${backend}/api/video/random?initData=${encodeURIComponent(initData)}`);
            if (!res.ok) throw new Error('Failed to fetch video: ' + res.status);
            const data = await res.json();

            this.currentVideo = data;
            this.video.src = data.video_url.startsWith('http') ? data.video_url : `${backend}${data.video_url}`;
            this.video.dataset.videoId = data.id;
        } catch (err) {
            console.error('Error loading random video:', err);
            throw err;
        }
    }

    async open() {
        try {
            await this.loadRandomVideo();
        } catch {
            alert('Не удалось загрузить видео.');
            return;
        }

        this.overlay.style.display = 'flex';
        this.video.currentTime = 0;
        this.video.dataset.maxTime = 0;
        this.canSkip = false;
        this.watchedPercentage = 0;
        this.closeBtn.style.display = 'none';

        this.video.play().catch(err => console.error('Video play error:', err));

        // haptic feedback if available
        try {
            const tg = window.Telegram?.WebApp;
            if (CONFIG.hapticFeedback && tg?.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('medium');
            }
        } catch {}
    }

    close() {
        if (!this.canSkip && this.watchedPercentage < CONFIG.videoRequiredWatchPercentage) {
            try {
                const tg = window.Telegram?.WebApp;
                if (CONFIG.hapticFeedback && tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('error');
                }
            } catch {}
            return;
        }
        this.overlay.style.display = 'none';
        this.video.pause();
    }

    onProgress() {
        const percentage = this.video.duration ? (this.video.currentTime / this.video.duration) * 100 : 0;
        this.watchedPercentage = percentage;
        this.progressBar.style.width = percentage + '%';

        if (this.video.currentTime > (this.video.dataset.maxTime || 0)) {
            this.video.dataset.maxTime = this.video.currentTime;
        }

        if (percentage >= CONFIG.videoRequiredWatchPercentage && !this.canSkip) {
            this.canSkip = true;
            this.closeBtn.style.display = 'block';
        }
    }

    onVideoEnd() {
        this.close();
        this.notifyBackendWatched();
    }

    async notifyBackendWatched() {
        try {
            const backend = window.location.origin;
            const videoId = this.video.dataset.videoId;
            const tg = window.Telegram?.WebApp;
            const userId = tg?.initDataUnsafe?.user?.id;

            if (!videoId || !userId) return;

            await fetch(`${backend}/api/video/watched`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: Number(videoId), telegram_id: Number(userId) })
            });
        } catch (err) {
            console.error('Failed to notify backend about watched video:', err);
        }
    }
}
