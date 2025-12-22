// ==================== VIDEO PLAYER ====================
class VideoPlayer {
    constructor(app) {
        this.app = app;
        this.overlay = document.getElementById('video-overlay');
        this.video = document.getElementById('video-player');
        this.closeBtn = document.getElementById('video-close');
        this.progressBar = document.getElementById('progress-bar');
        this.timerCount = document.getElementById('timer-count');
        this.timerCircle = document.getElementById('timer-progress');
        this.timerBtn = document.getElementById('video-timer');
        this.canSkip = false;
        this.watchedPercentage = 0;
        this.currentVideo = null;   
        this.requiredTime = 15;
        this.rewardClaimed = false;

        this.init();
    }

    init() {
        this.video.addEventListener('timeupdate', () => this.onProgress());
        this.video.addEventListener('ended', () => this.onVideoEnd());
        this.closeBtn.addEventListener('click', () => {
            if (this.canSkip) {
                this.close(true); // Закрыть сразу, если время вышло
            } else {
                this.handleUnfinishedClose();
            }
        });

        if (this.timerBtn) {
            this.timerBtn.addEventListener('click', () => {
                if (this.canSkip) {
                    this.close(true);
                }
            });
        }

        this.video.addEventListener('seeking', () => {
            if (this.video.currentTime > (this.video.dataset.maxTime || 0)) {
                this.video.currentTime = this.video.dataset.maxTime || 0;
            }
        });
    }

    handleUnfinishedClose() {
        this.video.pause();
        const tg = window.Telegram?.WebApp;
        
        // Используем нативный попап телеграма
        tg.showConfirm("Вы точно хотите выйти? Награда не будет получена.", (isConfirmed) => {
            if (isConfirmed) {
                this.close(true);
            } else {
                this.video.play();
            }
        });
    }

    async loadRandomVideo() {
        try {
            const backend = window.location.origin; 
            const initData = window.Telegram.WebApp.initData;
            
            console.log("[Video] Fetching from:", `${backend}/api/video/random`);
            
            const res = await fetch(`${backend}/api/video/random?initData=${encodeURIComponent(initData)}`);
            if (!res.ok) throw new Error('Failed to fetch video: ' + res.status);
            
            const data = await res.json();
            console.log("[Video] Data received from server:", data);

            this.currentVideo = data;

            // Формируем финальную ссылку
            let finalUrl;
            if (data.video_url.startsWith('http')) {
                finalUrl = data.video_url;
            } else {
                // Добавляем проверку на слэш между доменом и путем
                const cleanBackend = backend.replace(/\/$/, "");
                const cleanPath = data.video_url.startsWith('/') ? data.video_url : `/${data.video_url}`;
                finalUrl = `${cleanBackend}${cleanPath}`;
            }

            console.log("[Video] Final URL for player:", finalUrl);
            
            this.video.src = finalUrl;
            this.video.dataset.videoId = data.id;
            
        } catch (err) {
            console.error('[Video] Error loading random video:', err);
            throw err;
        }
    }

    async open() {

        this.rewardClaimed = false;

        if (this.timerBtn) this.timerBtn.classList.remove('finished');
        if (this.timerCount) {
            this.timerCount.innerHTML = this.requiredTime;
            this.timerCount.style.fontSize = ""; // Возвращаем размер шрифта
        }

        try {
            await this.loadRandomVideo();
        } catch {
            alert('Не удалось загрузить видео.');
            return;
        }

        this.overlay.classList.add('active');
        this.video.currentTime = 0;
        this.canSkip = false;
        this.watchedPercentage = 0;

        this.updateTimerUI(this.requiredTime);

        this.video.play().catch(() => {
            this.canSkip = true; // Если автоплей заблокирован
        });
    }

    close(force = false) {
        if (!force && !this.canSkip) return;
        
        this.overlay.classList.remove('active');
        this.video.pause();
        this.video.src = ""; // Очистка ресурса
        this.app.updateUI();
    }

    onProgress() {
        const currentTime = Math.floor(this.video.currentTime);
        const remaining = Math.max(0, this.requiredTime - currentTime);
        
        this.updateTimerUI(remaining);

        if (remaining === 0 && !this.rewardClaimed) {
            this.canSkip = true;
            this.rewardClaimed = true; // Блокируем повторный вызов
            this.handleVideoSuccess(); // Отправляем запрос на награду   
        }
        
        // Твоя старая логика прогресс-бара
        if (this.video.duration) {
            this.watchedPercentage = (this.video.currentTime / this.video.duration) * 100;
            if (this.progressBar) this.progressBar.style.width = this.watchedPercentage + '%';
        }   
    }

    handleVideoSuccess() {
        // 1. Меняем внешний вид кнопки таймера
        if (this.timerBtn) this.timerBtn.classList.add('finished');
        if (this.timerCount) {
            this.timerCount.innerHTML = '➜'; // Стрелочка
            this.timerCount.style.fontSize = '24px';
        }

        // 2. Отправляем данные на сервер
        this.notifyBackendWatched();

        // 3. Обратная связь
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        }
        
        // 4. Показываем всплывашку с наградой (из твоего app.js)
        this.app.showRewardPopup(0.05);
    }

    updateTimerUI(seconds) {
        if (this.canSkip && seconds === 0) return;

        if (this.timerCount) this.timerCount.innerText = seconds;
        
        // Рассчет круга: (остаток / всего) * 100
        if (this.timerCircle) {
            const offset = (seconds / this.requiredTime) * 100;
            this.timerCircle.setAttribute('stroke-dasharray', `${offset}, 100`);
        }
    }

    onVideoEnd() {
        if (!this.rewardClaimed) {
            this.rewardClaimed = true;
            this.canSkip = true;
            this.notifyBackendWatched();
        }

        this.updateTimerUI(0);
        this.close(true);
    }

    async notifyBackendWatched() {
        try {
            const backend = window.location.origin;
            const videoId = this.video.dataset.videoId;
            const tg = window.Telegram?.WebApp;
            const userId = tg?.initDataUnsafe?.user?.id;

            if (!videoId || !userId) return;

            await this.app.apiRequest('/video/watched', 'POST', { 
                video_id: Number(videoId) 
            });

            const currentWatched = this.app.state.getCounter('videos_watched');
            this.app.state.counters['videos_watched'] = currentWatched + 1;
            this.app.state.addToBalance(0.05);
            
        } catch (err) {
            console.error('Failed to notify backend about watched video:', err);
        }
    }
}
