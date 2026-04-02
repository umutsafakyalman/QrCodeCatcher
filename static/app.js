/**
 * QR Code Catcher — Frontend Logic
 * SSE ile gerçek zamanlı tarama takibi
 * Playlist desteği ile çoklu video tarama
 */

let eventSource = null;
let isScanning = false;
let isPaused = false;
let isPlaylist = false;
let totalQrFound = 0;
let currentScanId = null;
let currentLang = 'tr';

const translations = {
    'tr': {
        'logo_subtitle': 'YouTube Video QR Tarayıcı',
        'input_title': 'Video veya Playlist Linkini Yapıştır',
        'input_desc': 'YouTube video veya playlist linkini aşağıya yapıştırın. Sistem tüm videoları indirecek, her kareyi tarayacak ve gizli QR kodları bulacak.',
        'input_placeholder': 'https://www.youtube.com/watch?v=...',
        'scan_btn': 'Taramayı Başlat',
        'scan_precision': 'Tarama Hassasiyeti:',
        'prec_high': 'Çok Yüksek (Her frame)',
        'prec_normal': 'Normal (Her 3 frame)',
        'prec_fast': 'Hızlı (Her 5 frame)',
        'prec_very_fast': 'Çok Hızlı (Her 10 frame)',
        'scanning': 'Taranıyor...',
        'pause': 'Duraklat',
        'stop': 'Durdur',
        'video_label': 'Video',
        'live_findings': 'Canlı Bulgular: ',
        'scan_complete': 'Tarama Tamamlandı',
        'qr_found': 'QR KOD BULUNDU',
        'scanned_videos': 'VİDEO TARANDI',
        'scanned_frames': 'FRAME TARANDI',
        'no_qr_found': 'Bu videoda QR kod bulunamadı.',
        'try_again': 'Farklı hassasiyet ayarıyla tekrar deneyin veya başka bir video linkiyle tarayın.',
        'new_scan': 'Yeni Tarama Başlat',
        
        // JS dynamic strings
        'error_url': 'Bir hata oluştu',
        'error_conn': 'Sunucuya bağlanılamadı: ',
        'error_disconnect': 'Bağlantı kesildi',
        'status_init': 'Link Analiz Ediliyor...',
        'status_down_pl': 'Video İndiriliyor...',
        'status_down': 'Video İndiriliyor...',
        'status_scan': 'QR Kod Taranıyor...',
        'status_pl': 'Playlist Yükleniyor...',
        'log_playlist': (title, count) => `📋 Playlist: ${title} — ${count} video`,
        'log_video': (num, total, title) => `📹 Video ${num}/${total}: ${title}`,
        'paused_title': '⏸️ Duraklatıldı',
        'stopped_title': '🛑 Tarama Durduruldu',
        'stopped_subtitle': 'Kısmi sonuçlar gösteriliyor',
        'results_loading': 'Sonuçlar Yükleniyor...',
        'results_found_title': 'QR Kodlar Bulundu!',
        'results_pl_sub': (v, q) => `${v} video tarandı, ${q} QR kod tespit edildi`,
        'results_vi_sub': (q) => `${q} adet QR kod tespit edildi`,
        'results_not_pl_sub': (v, f) => `${v} video, ${f} frame tarandı — QR kod bulunamadı`,
        'results_not_vi_sub': (f) => `${f} frame tarandı, QR kod bulunamadı`,
        'btn_copy': '📋 Kopyala',
        'btn_copied': '✅ Kopyalandı!',
        'btn_open': '🔗 Linki Aç',
        'badge_noqr': 'QR Yok',
        'badge_error': 'Hata',
        'badge_qr': (c) => `${c} QR`,
        'group_error': (e) => `Hata: ${e}`,
        'group_empty': 'Bu videoda QR kod bulunamadı'
    },
    'en': {
        'logo_subtitle': 'YouTube Video QR Scanner',
        'input_title': 'Paste Video or Playlist Link',
        'input_desc': 'Paste the YouTube video or playlist link below. The system will download all videos, scan every frame, and find hidden QR codes.',
        'input_placeholder': 'https://www.youtube.com/watch?v=...',
        'scan_btn': 'Start Scan',
        'scan_precision': 'Scan Precision:',
        'prec_high': 'Very High (Every frame)',
        'prec_normal': 'Normal (Every 3 frames)',
        'prec_fast': 'Fast (Every 5 frames)',
        'prec_very_fast': 'Very Fast (Every 10 frames)',
        'scanning': 'Scanning...',
        'pause': 'Pause',
        'stop': 'Stop',
        'video_label': 'Video',
        'live_findings': 'Live Findings: ',
        'scan_complete': 'Scan Completed',
        'qr_found': 'QR CODES FOUND',
        'scanned_videos': 'VIDEOS SCANNED',
        'scanned_frames': 'FRAMES SCANNED',
        'no_qr_found': 'No QR codes found in this video.',
        'try_again': 'Try again with a different precision setting or scan another video link.',
        'new_scan': 'Start New Scan',

        // JS dynamic strings
        'error_url': 'An error occurred',
        'error_conn': 'Could not connect to server: ',
        'error_disconnect': 'Connection lost',
        'status_init': 'Analyzing Link...',
        'status_down_pl': 'Downloading Video...',
        'status_down': 'Downloading Video...',
        'status_scan': 'Scanning QR Codes...',
        'status_pl': 'Loading Playlist...',
        'log_playlist': (title, count) => `📋 Playlist: ${title} — ${count} videos`,
        'log_video': (num, total, title) => `📹 Video ${num}/${total}: ${title}`,
        'paused_title': '⏸️ Paused',
        'stopped_title': '🛑 Scan Stopped',
        'stopped_subtitle': 'Showing partial results',
        'results_loading': 'Loading Results...',
        'results_found_title': 'QR Codes Found!',
        'results_pl_sub': (v, q) => `${v} videos scanned, ${q} QR codes detected`,
        'results_vi_sub': (q) => `${q} QR codes detected`,
        'results_not_pl_sub': (v, f) => `${v} videos, ${f} frames scanned — No QR codes found`,
        'results_not_vi_sub': (f) => `${f} frames scanned, No QR codes found`,
        'btn_copy': '📋 Copy',
        'btn_copied': '✅ Copied!',
        'btn_open': '🔗 Open Link',
        'badge_noqr': 'No QR',
        'badge_error': 'Error',
        'badge_qr': (c) => `${c} QR`,
        'group_error': (e) => `Error: ${e}`,
        'group_empty': 'No QR codes found in this video'
    }
};

function t(key, ...args) {
    const val = translations[currentLang][key] || key;
    if (typeof val === 'function') {
        return val(...args);
    }
    return val;
}

function setLanguage(lang) {
    if (!['tr', 'en'].includes(lang)) return;
    currentLang = lang;
    
    // Update active button
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`lang-${lang}`).classList.add('active');

    // Update static UI elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.getAttribute('data-i18n'));
    });
    
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        el.title = t(el.getAttribute('data-i18n-title'));
    });
    
    // Refresh Dynamic states if any
    if (isScanning && !isPaused) {
        progressTitle.textContent = t('scanning');
    } else if (isPaused) {
        progressTitle.textContent = t('paused_title');
    } else if (!isScanning && scanBtn.disabled) {
        scanBtn.querySelector('span').textContent = t('scan_btn');
    }
}

// ========== UI Elements ==========
const urlInput = document.getElementById('url-input');
const scanBtn = document.getElementById('scan-btn');
const inputSection = document.getElementById('input-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const progressFill = document.getElementById('progress-fill');
const progressPct = document.getElementById('progress-pct');
const progressTitle = document.getElementById('progress-title');
const progressSubtitle = document.getElementById('progress-subtitle');
const logEntries = document.getElementById('log-entries');
const logContainer = document.getElementById('log-container');
const videoInfo = document.getElementById('video-info');
const videoTitle = document.getElementById('video-title');
const liveResults = document.getElementById('live-results');
const liveQrList = document.getElementById('live-qr-list');
const qrCount = document.getElementById('qr-count');
const playlistBanner = document.getElementById('playlist-banner');
const playlistTitle = document.getElementById('playlist-title');
const playlistVideoCount = document.getElementById('playlist-video-count');
const videoCounter = document.getElementById('video-counter');
const videoCounterValue = document.getElementById('video-counter-value');
const videoCounterTitle = document.getElementById('video-counter-title');

// Enter tuşu ile tarama başlat
urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startScan();
});

// ========== Start Scan ==========
async function startScan() {
    const url = urlInput.value.trim();
    if (!url) {
        shakeInput();
        return;
    }

    if (isScanning) return;
    isScanning = true;
    isPlaylist = false;
    isPaused = false;
    totalQrFound = 0;
    currentScanId = null;

    const skipFrames = document.getElementById('skip-frames').value;

    // UI güncelle
    scanBtn.disabled = true;
    scanBtn.classList.add('scanning');
    scanBtn.querySelector('span').textContent = t('scanning');
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    resetProgress();

    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, skip_frames: parseInt(skipFrames) })
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(data.error || t('error_url'), 'error');
            resetScanBtn();
            return;
        }

        // SSE bağlantısı kur
        currentScanId = data.scan_id;
        connectSSE(data.scan_id);
    } catch (err) {
        addLog(t('error_conn') + err.message, 'error');
        resetScanBtn();
    }
}

// ========== SSE Connection ==========
function connectSSE(scanId) {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/api/events/${scanId}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);
    };

    eventSource.onerror = () => {
        if (isScanning) {
            addLog(t('error_disconnect'), 'error');
            resetScanBtn();
        }
        eventSource.close();
    };
}

// ========== Handle SSE Events ==========
function handleEvent(data) {
    switch (data.type) {
        case 'status':
            handleStatus(data);
            break;
        case 'playlist_info':
            handlePlaylistInfo(data);
            break;
        case 'video_start':
            handleVideoStart(data);
            break;
        case 'video_info':
            handleVideoInfo(data);
            break;
        case 'video_complete':
            handleVideoComplete(data);
            break;
        case 'video_error':
            handleVideoError(data);
            break;
        case 'qr_found':
            handleQRFound(data);
            break;
        case 'paused':
            handlePaused(data);
            break;
        case 'resumed':
            handleResumed(data);
            break;
        case 'stopped':
            handleStopped(data);
            break;
        case 'complete':
            handleComplete(data);
            break;
        case 'error':
            handleError(data);
            break;
        case 'keepalive':
            break;
    }
}

function handleStatus(data) {
    const progress = data.progress || 0;
    progressFill.style.width = `${progress}%`;
    progressPct.textContent = `${progress}%`;

    if (data.stage === 'init') {
        progressTitle.textContent = t('status_init');
    } else if (data.stage === 'download') {
        progressTitle.textContent = isPlaylist ? t('status_down_pl') : t('status_down');
    } else if (data.stage === 'scan') {
        progressTitle.textContent = t('status_scan');
    } else if (data.stage === 'playlist') {
        progressTitle.textContent = t('status_pl');
    }

    progressSubtitle.textContent = data.message || '';
    document.getElementById('progress-bar').classList.add('active');

    addLog(data.message);
}

function handlePlaylistInfo(data) {
    isPlaylist = data.is_playlist;

    if (data.is_playlist) {
        playlistBanner.classList.remove('hidden');
        playlistTitle.textContent = data.playlist_title;
        playlistVideoCount.textContent = `${data.total_videos} ${t('video_label').toLowerCase()}`;

        addLog(t('log_playlist', data.playlist_title, data.total_videos), 'found');
    }
}

function handleVideoStart(data) {
    if (isPlaylist) {
        videoCounter.classList.remove('hidden');
        videoCounterValue.textContent = `${data.video_num}/${data.total_videos}`;
        videoCounterTitle.textContent = data.title;

        // Progress bar sıfırla (her video için)
        progressFill.style.width = '0%';
        progressPct.textContent = '0%';
    }

    addLog(t('log_video', data.video_num, data.total_videos, data.title));
}

function handleVideoInfo(data) {
    videoInfo.classList.remove('hidden');
    const prefix = isPlaylist ? `[${data.video_num}/${data.total_videos}] ` : '';
    videoTitle.textContent = `🎬 ${prefix}${data.title}`;
}

function handleVideoComplete(data) {
    addLog(data.message, data.qr_count > 0 ? 'found' : '');
}

function handleVideoError(data) {
    addLog(data.message, 'error');
}

function handleQRFound(data) {
    liveResults.classList.remove('hidden');
    totalQrFound++;
    qrCount.textContent = totalQrFound;

    const item = document.createElement('div');
    item.className = 'live-qr-item';

    const videoLabel = data.video_title
        ? `<span style="color: var(--text-muted); font-size: 0.75rem;">${escapeHtml(data.video_title)}</span><br>`
        : '';

    item.innerHTML = `${videoLabel}<div class="live-qr-data">${escapeHtml(data.message)}</div>`;
    liveQrList.appendChild(item);

    addLog(data.message, 'found');
}

function handleComplete(data) {
    if (eventSource) eventSource.close();
    resetScanBtn();
    currentScanId = null;

    const results = data.results;
    progressFill.style.width = '100%';
    progressPct.textContent = '100%';

    // Kısa gecikme ile sonuç ekranına geçiş
    setTimeout(() => {
        showResults(results);
    }, 800);
}

function handleError(data) {
    if (eventSource) eventSource.close();
    addLog(data.message, 'error');
    resetScanBtn();
    currentScanId = null;
}

function handlePaused(data) {
    isPaused = true;
    addLog(data.message, 'found');
    progressTitle.textContent = t('paused_title');

    // UI güncelle
    document.getElementById('pause-btn').classList.add('paused');
    document.getElementById('pause-icon').classList.add('hidden');
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('scanner-anim').classList.add('paused');
}

function handleResumed(data) {
    isPaused = false;
    addLog(data.message);
    progressTitle.textContent = t('scanning');

    // UI güncelle
    document.getElementById('pause-btn').classList.remove('paused');
    document.getElementById('pause-icon').classList.remove('hidden');
    document.getElementById('play-icon').classList.add('hidden');
    document.getElementById('scanner-anim').classList.remove('paused');
}

function handleStopped(data) {
    if (eventSource) eventSource.close();
    resetScanBtn();
    currentScanId = null;
    addLog(data.message, 'error');

    // Eğer kısmi sonuçlar varsa göster
    if (data.results) {
        setTimeout(() => {
            showResults(data.results);
            document.getElementById('results-title').textContent = t('stopped_title');
            document.getElementById('results-icon').textContent = '🛑';
            document.getElementById('results-subtitle').textContent = t('stopped_subtitle');
        }, 500);
    } else {
        setTimeout(() => {
            progressSection.classList.add('hidden');
        }, 1000);
    }
}

// ========== Pause / Stop ==========
async function togglePause() {
    if (!currentScanId || !isScanning) return;

    try {
        await fetch(`/api/pause/${currentScanId}`, { method: 'POST' });
    } catch (err) {
        addLog('Pause hatası: ' + err.message, 'error');
    }
}

async function stopScan() {
    if (!currentScanId || !isScanning) return;

    const stopBtn = document.getElementById('stop-btn');
    stopBtn.disabled = true;

    try {
        await fetch(`/api/stop/${currentScanId}`, { method: 'POST' });
        addLog('🛑 Durdurma sinyali gönderildi...');
    } catch (err) {
        addLog('Stop hatası: ' + err.message, 'error');
    }
}

// ========== Show Results ==========
function showResults(results) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    const videos = results.videos || [];
    const totalQR = results.total_qr_found || 0;
    const totalFrames = results.total_frames_scanned || 0;
    const totalVideos = results.total_videos || videos.length;

    // İstatistikler
    document.getElementById('stat-qr').textContent = totalQR;
    document.getElementById('stat-videos').textContent = totalVideos;
    document.getElementById('stat-frames').textContent = totalFrames.toLocaleString();

    if (totalQR > 0) {
        document.getElementById('results-icon').textContent = '🎯';
        document.getElementById('results-title').textContent = t('results_found_title');

        const subtitle = results.is_playlist
            ? t('results_pl_sub', totalVideos, totalQR)
            : t('results_vi_sub', totalQR);
        document.getElementById('results-subtitle').textContent = subtitle;

        document.getElementById('no-results').classList.add('hidden');
    } else {
        document.getElementById('results-icon').textContent = '🔍';
        document.getElementById('results-title').textContent = t('scan_complete');

        const subtitle = results.is_playlist
            ? t('results_not_pl_sub', totalVideos, totalFrames.toLocaleString())
            : t('results_not_vi_sub', totalFrames.toLocaleString());
        document.getElementById('results-subtitle').textContent = subtitle;

        document.getElementById('no-results').classList.remove('hidden');
    }

    // Sonuçları render et
    if (results.is_playlist) {
        renderPlaylistResults(videos);
    } else {
        // Tek video — eski format
        const allQRCodes = [];
        videos.forEach(v => {
            if (v.qr_codes) allQRCodes.push(...v.qr_codes);
        });
        renderQRCards(allQRCodes);
    }
}

function renderPlaylistResults(videos) {
    const list = document.getElementById('qr-results-list');
    list.innerHTML = '';

    videos.forEach((video, vIdx) => {
        const group = document.createElement('div');
        group.className = 'video-group';
        group.style.animationDelay = `${vIdx * 0.1}s`;

        const hasError = video.error;
        const qrCodes = video.qr_codes || [];
        const hasQR = qrCodes.length > 0;

        let badgeClass = 'no-qr';
        let badgeText = t('badge_noqr');
        if (hasError) {
            badgeClass = 'error';
            badgeText = t('badge_error');
        } else if (hasQR) {
            badgeClass = 'has-qr';
            badgeText = t('badge_qr', qrCodes.length);
        }

        const meta = hasError
            ? t('group_error', video.error)
            : `${video.scanned_frames?.toLocaleString() || '?'} frame • ${video.duration_formatted || '?'}`;

        group.innerHTML = `
            <div class="video-group-header">
                <div class="video-group-number">${video.video_num || vIdx + 1}</div>
                <div class="video-group-info">
                    <div class="video-group-title">${escapeHtml(video.title)}</div>
                    <div class="video-group-meta">${meta}</div>
                </div>
                <span class="video-group-badge ${badgeClass}">${badgeText}</span>
            </div>
        `;

        if (hasQR) {
            const cardsContainer = document.createElement('div');
            cardsContainer.className = 'video-group-cards';

            qrCodes.forEach((qr, qrIdx) => {
                const card = createQRCard(qr, qrIdx);
                cardsContainer.appendChild(card);
            });

            group.appendChild(cardsContainer);
        } else if (!hasError) {
            const emptyEl = document.createElement('div');
            emptyEl.className = 'video-group-empty';
            emptyEl.textContent = t('group_empty');
            group.appendChild(emptyEl);
        }

        list.appendChild(group);
    });
}

function createQRCard(qr, index) {
    const isUrl = qr.data.startsWith('http://') || qr.data.startsWith('https://');
    const displayData = isUrl
        ? `<a href="${escapeHtml(qr.data)}" target="_blank" rel="noopener">${escapeHtml(qr.data)}</a>`
        : escapeHtml(qr.data);

    const card = document.createElement('div');
    card.className = 'qr-result-card';
    card.style.animationDelay = `${index * 0.1}s`;

    card.innerHTML = `
        <div class="qr-result-content">
            <img class="qr-snapshot" src="${qr.snapshot}" alt="QR Code Frame"
                 onerror="this.style.display='none'">
            <div class="qr-details">
                <div class="qr-badge-row">
                    <span class="qr-badge">📌 ${qr.type || 'QRCODE'}</span>
                    <span class="qr-timestamp">⏱ ${qr.timestamp_formatted} | Frame #${qr.frame}</span>
                </div>
                <div class="qr-data-label">İçerik</div>
                <div class="qr-data-value">${displayData}</div>
                <div class="qr-actions">
                    <button class="qr-action-btn" onclick="copyToClipboard('${escapeJs(qr.data)}', this)">
                        ${t('btn_copy')}
                    </button>
                    ${isUrl ? `<button class="qr-action-btn" onclick="window.open('${escapeJs(qr.data)}', '_blank')">
                        ${t('btn_open')}
                    </button>` : ''}
                </div>
            </div>
        </div>
    `;

    return card;
}

function renderQRCards(qrCodes) {
    const list = document.getElementById('qr-results-list');
    list.innerHTML = '';

    qrCodes.forEach((qr, index) => {
        const card = createQRCard(qr, index);
        list.appendChild(card);
    });
}

// ========== UI Helpers ==========
function resetProgress() {
    progressFill.style.width = '0%';
    progressPct.textContent = '0%';
    progressTitle.textContent = t('scanning');
    progressSubtitle.textContent = '';
    logEntries.innerHTML = '';
    videoInfo.classList.add('hidden');
    liveResults.classList.add('hidden');
    liveQrList.innerHTML = '';
    qrCount.textContent = '0';
    playlistBanner.classList.add('hidden');
    videoCounter.classList.add('hidden');
    document.getElementById('progress-bar').classList.remove('active');
    totalQrFound = 0;
    isPaused = false;

    // Butonları sıfırla
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    pauseBtn.classList.remove('paused');
    pauseBtn.disabled = false;
    stopBtn.disabled = false;
    document.getElementById('pause-icon').classList.remove('hidden');
    document.getElementById('play-icon').classList.add('hidden');
    document.getElementById('scanner-anim').classList.remove('paused');
}

function resetScanBtn() {
    isScanning = false;
    isPaused = false;
    scanBtn.disabled = false;
    scanBtn.classList.remove('scanning');
    scanBtn.querySelector('span').textContent = t('scan_btn');
}

function resetUI() {
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    urlInput.value = '';
    urlInput.focus();
}

function addLog(message, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;

    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    entry.innerHTML = `<span class="log-time">[${time}]</span>${escapeHtml(message)}`;
    logEntries.appendChild(entry);

    // Otomatik scroll
    logContainer.scrollTop = logContainer.scrollHeight;
}

function shakeInput() {
    urlInput.style.animation = 'none';
    urlInput.offsetHeight; // reflow
    urlInput.style.animation = 'shake 0.4s ease';
    urlInput.style.borderColor = 'var(--accent-red)';
    setTimeout(() => {
        urlInput.style.borderColor = '';
    }, 1000);
}

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const original = btn.innerHTML;
        btn.innerHTML = t('btn_copied');
        btn.style.borderColor = 'var(--accent-green)';
        setTimeout(() => {
            btn.innerHTML = original;
            btn.style.borderColor = '';
        }, 2000);
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeJs(text) {
    return text.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Shake animation CSS inject
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        20% { transform: translateX(-8px); }
        40% { transform: translateX(8px); }
        60% { transform: translateX(-4px); }
        80% { transform: translateX(4px); }
    }
`;
document.head.appendChild(style);
