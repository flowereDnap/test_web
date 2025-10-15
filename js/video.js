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

        this.closeBtn.addEventListener('click', (e) => {
            console.log('video close clicked', this.canSkip, this.watchedPercentage);
            this.close();
        });

        this.video.addEventListener('seeking', (e) => {
            if (this.video.currentTime > this.video.dataset.maxTime || 0) {
                this.video.currentTime = this.video.dataset.maxTime || 0;
            }
        });
    }

    async loadRandomVideo() {
        try {
            const res = await fetch('/api/video/random');
            if (!res.ok) throw new Error('Failed to fetch video');
            const data = await res.json();
            this.currentVideo = data;
            this.video.src = data.video_url;
        } catch (err) {
            console.error('Error loading random video:', err);
        }
    }

    async open() {
        await this.loadRandomVideo();

        if (!this.currentVideo) return;

        this.overlay.classList.add('active');
        this.video.currentTime = 0;
        this.video.dataset.maxTime = 0;
        this.canSkip = false;
        this.watchedPercentage = 0;
        this.closeBtn.classList.remove('show');

        this.video.play().catch(err => {
            console.error('Video play error:', err);
        });

        if (CONFIG.hapticFeedback && this.app.tg.HapticFeedback) {
            this.app.tg.HapticFeedback.impactOccurred('medium');
        }
    }

    close() {
        if (!this.canSkip && this.watchedPercentage < CONFIG.videoRequiredWatchPercentage) {
            if (CONFIG.hapticFeedback && this.app.tg.HapticFeedback) {
                this.app.tg.HapticFeedback.notificationOccurred('error');
            }
            return;
        }

        this.overlay.classList.remove('active');
        this.video.pause();
    }

    onProgress() {
        const percentage = (this.video.currentTime / this.video.duration) * 100;
        this.watchedPercentage = percentage;
        this.progressBar.style.width = percentage + '%';

        if (this.video.currentTime > (this.video.dataset.maxTime || 0)) {
            this.video.dataset.maxTime = this.video.currentTime;
        }

        if (percentage >= CONFIG.videoRequiredWatchPercentage && !this.canSkip) {
            this.canSkip = true;
            this.closeBtn.classList.add('show');
        }
    }

    onVideoEnd() {
        this.close();
        this.app.onVideoComplete(this.currentVideo);
    }
}
