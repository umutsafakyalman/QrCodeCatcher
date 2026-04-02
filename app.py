"""
QR Code Catcher — Flask Web Server
YouTube videolarındaki gizli QR kodları yakalar.
Playlist desteği ile tüm videoları tarar.
"""

import os
import json
import uuid
import queue
import threading
from flask import Flask, render_template, request, jsonify, Response
from scanner import QRCodeScanner

app = Flask(__name__)
scanner = QRCodeScanner()

# SSE event queues — her istemci için ayrı kuyruk
scan_queues = {}

# Tarama kontrol sinyalleri — pause/stop
# Her scan_id için: {'pause': threading.Event, 'stop': threading.Event}
scan_controls = {}


@app.route('/')
def index():
    """Ana sayfa."""
    return render_template('index.html')


@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Tarama başlat."""
    data = request.get_json()
    url = data.get('url', '').strip()
    skip_frames = int(data.get('skip_frames', 3))

    if not url:
        return jsonify({'error': 'URL gerekli'}), 400

    # YouTube URL doğrulama
    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        return jsonify({'error': 'Geçerli bir YouTube linki giriniz'}), 400

    # Benzersiz scan ID oluştur
    scan_id = str(uuid.uuid4())[:8]
    scan_queues[scan_id] = queue.Queue()

    # Kontrol sinyalleri oluştur
    pause_event = threading.Event()
    stop_event = threading.Event()
    scan_controls[scan_id] = {'pause': pause_event, 'stop': stop_event}

    # Taramayı arka planda başlat
    thread = threading.Thread(
        target=_run_scan,
        args=(scan_id, url, skip_frames),
        daemon=True
    )
    thread.start()

    return jsonify({'scan_id': scan_id})


@app.route('/api/pause/<scan_id>', methods=['POST'])
def pause_scan(scan_id):
    """Taramayı duraklat veya devam ettir."""
    ctrl = scan_controls.get(scan_id)
    if not ctrl:
        return jsonify({'error': 'Tarama bulunamadı'}), 404

    q = scan_queues.get(scan_id)
    if ctrl['pause'].is_set():
        # Devam ettir
        ctrl['pause'].clear()
        if q:
            q.put({'type': 'resumed', 'message': '▶️ Tarama devam ediyor...'})
        return jsonify({'paused': False})
    else:
        # Duraklat
        ctrl['pause'].set()
        if q:
            q.put({'type': 'paused', 'message': '⏸️ Tarama duraklatıldı'})
        return jsonify({'paused': True})


@app.route('/api/stop/<scan_id>', methods=['POST'])
def stop_scan(scan_id):
    """Taramayı tamamen durdur."""
    ctrl = scan_controls.get(scan_id)
    if not ctrl:
        return jsonify({'error': 'Tarama bulunamadı'}), 404

    ctrl['stop'].set()
    ctrl['pause'].set()  # Pause'dan da çıkart ki stop işlensin
    # Mesaj _run_scan içinden gönderilecek
    return jsonify({'stopped': True})


@app.route('/api/events/<scan_id>')
def scan_events(scan_id):
    """SSE (Server-Sent Events) ile gerçek zamanlı ilerleme."""
    def generate():
        q = scan_queues.get(scan_id)
        if not q:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Geçersiz tarama ID'})}\n\n"
            return

        while True:
            try:
                event = q.get(timeout=180)
                yield f"data: {json.dumps(event)}\n\n"

                if event.get('type') in ('complete', 'error', 'stopped'):
                    # Temizlik
                    scan_queues.pop(scan_id, None)
                    scan_controls.pop(scan_id, None)
                    break
            except queue.Empty:
                # Keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


def _check_controls(scan_id, q):
    """Pause/stop sinyallerini kontrol et. Stop ise True döner."""
    ctrl = scan_controls.get(scan_id)
    if not ctrl:
        return False

    # Stop kontrolü
    if ctrl['stop'].is_set():
        return True

    # Pause kontrolü — duraklatıldıysa bekle
    while ctrl['pause'].is_set():
        if ctrl['stop'].is_set():
            return True
        import time
        time.sleep(0.2)

    return False


def _run_scan(scan_id, url, skip_frames):
    """Taramayı arka planda çalıştır — tekli video ve playlist destekli."""
    q = scan_queues.get(scan_id)
    if not q:
        return

    try:
        # Aşama 0: Playlist mi kontrol et
        q.put({
            'type': 'status',
            'stage': 'init',
            'progress': 0,
            'message': 'Link analiz ediliyor...'
        })

        def init_progress(stage, progress, message):
            q.put({
                'type': 'status',
                'stage': stage,
                'progress': progress,
                'message': message
            })

        if _check_controls(scan_id, q):
            q.put({'type': 'stopped', 'message': '🛑 Tarama durduruldu'})
            return

        playlist_info = scanner.extract_playlist(url, progress_callback=init_progress)

        is_playlist = playlist_info['is_playlist']
        videos = playlist_info['videos']
        total_videos = playlist_info['count']

        if total_videos == 0:
            q.put({'type': 'error', 'message': 'Playlist boş veya videolar bulunamadı'})
            return

        # Playlist bilgisini gönder
        q.put({
            'type': 'playlist_info',
            'is_playlist': is_playlist,
            'playlist_title': playlist_info['title'],
            'total_videos': total_videos,
        })

        # Her video için sonuçları topla
        all_video_results = []
        total_qr_found = 0
        total_frames_scanned = 0

        for video_idx, video_entry in enumerate(videos):
            # Her video başında stop kontrolü
            if _check_controls(scan_id, q):
                q.put({
                    'type': 'stopped',
                    'message': '🛑 Tarama durduruldu',
                    'results': {
                        'is_playlist': is_playlist,
                        'playlist_title': playlist_info['title'],
                        'total_videos': total_videos,
                        'total_qr_found': total_qr_found,
                        'total_frames_scanned': total_frames_scanned,
                        'videos': all_video_results,
                    }
                })
                return

            video_url = video_entry['url']
            video_title = video_entry['title']
            video_num = video_idx + 1
            video_path = None

            try:
                # Video başlangıç bilgisi
                q.put({
                    'type': 'video_start',
                    'video_index': video_idx,
                    'video_num': video_num,
                    'total_videos': total_videos,
                    'title': video_title,
                })

                # Video indir
                def download_progress(stage, progress, message):
                    prefix = f"[{video_num}/{total_videos}] " if is_playlist else ""
                    q.put({
                        'type': 'status',
                        'stage': 'download',
                        'progress': progress,
                        'message': f"{prefix}{message}",
                        'video_num': video_num,
                        'total_videos': total_videos,
                    })

                video_info = scanner.download_video(video_url,
                    progress_callback=download_progress)
                video_path = video_info['path']

                q.put({
                    'type': 'video_info',
                    'title': video_info['title'],
                    'duration': video_info['duration'],
                    'video_id': video_info['video_id'],
                    'video_num': video_num,
                    'total_videos': total_videos,
                })

                # Frame tarama
                def scan_progress(stage, progress, message):
                    prefix = f"[{video_num}/{total_videos}] " if is_playlist else ""
                    if stage == 'found':
                        q.put({
                            'type': 'qr_found',
                            'stage': 'found',
                            'progress': progress,
                            'message': f"{prefix}{message}",
                            'video_title': video_info['title'],
                            'video_num': video_num,
                        })
                    else:
                        q.put({
                            'type': 'status',
                            'stage': 'scan',
                            'progress': progress,
                            'message': f"{prefix}{message}",
                            'video_num': video_num,
                            'total_videos': total_videos,
                        })

                # Kontrol sinyallerini scanner'a aktar
                ctrl = scan_controls.get(scan_id, {})
                results = scanner.scan_video(video_path, skip_frames=skip_frames,
                                             progress_callback=scan_progress,
                                             pause_event=ctrl.get('pause'),
                                             stop_event=ctrl.get('stop'))

                # Video sonuçlarını topla
                video_result = {
                    'title': video_info['title'],
                    'video_id': video_info['video_id'],
                    'video_num': video_num,
                    'duration_formatted': results['duration_formatted'],
                    'scanned_frames': results['scanned_frames'],
                    'total_frames': results['total_frames'],
                    'qr_codes': results['qr_codes'],
                }
                all_video_results.append(video_result)

                total_qr_found += len(results['qr_codes'])
                total_frames_scanned += results['scanned_frames']

                # Video tamamlandı bilgisi
                q.put({
                    'type': 'video_complete',
                    'video_num': video_num,
                    'total_videos': total_videos,
                    'title': video_info['title'],
                    'qr_count': len(results['qr_codes']),
                    'message': f"[{video_num}/{total_videos}] ✅ {video_info['title']} — "
                               f"{len(results['qr_codes'])} QR kod bulundu"
                })

            except Exception as e:
                q.put({
                    'type': 'video_error',
                    'video_num': video_num,
                    'total_videos': total_videos,
                    'title': video_title,
                    'message': f"[{video_num}/{total_videos}] ❌ {video_title}: {str(e)}"
                })
                all_video_results.append({
                    'title': video_title,
                    'video_id': '',
                    'video_num': video_num,
                    'error': str(e),
                    'qr_codes': [],
                })

            finally:
                if video_path:
                    scanner.cleanup(video_path)

        # Tüm tarama tamamlandı
        q.put({
            'type': 'complete',
            'results': {
                'is_playlist': is_playlist,
                'playlist_title': playlist_info['title'],
                'total_videos': total_videos,
                'total_qr_found': total_qr_found,
                'total_frames_scanned': total_frames_scanned,
                'videos': all_video_results,
            }
        })

    except Exception as e:
        q.put({
            'type': 'error',
            'message': str(e)
        })


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
