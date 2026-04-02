"""
YouTube Video QR Code Scanner — v2 Optimized
Videoları indirir, frame'leri tarar, QR kodları tespit eder.

Optimizasyonlar:
- grab() ile atlanan frame'lerde decode yok (5-10x hız)
- Frame'ler 640px'e küçültülüyor (tarama için yeterli)
- Sıkı QR doğrulama: min boyut, polygon, sadece QRCODE tipi
- Paralel frame işleme (ThreadPoolExecutor)
- Sahte QR tespiti engelleme
"""

import os
import time
import json
import hashlib
import cv2
import numpy as np
from pyzbar.pyzbar import decode as pyzbar_decode
from pyzbar.pyzbar import ZBarSymbol
from PIL import Image
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ===== Yapılandırma =====
SCAN_WIDTH = 640          # Tarama için frame genişliği (px)
MIN_QR_SIZE = 20          # Minimum QR boyutu (px) — bundan küçükler reddedilir
MIN_QR_DATA_LEN = 1       # Minimum QR veri uzunluğu
MAX_QR_DATA_LEN = 4096    # Maksimum QR veri uzunluğu
WORKER_THREADS = 4        # Paralel tarama thread sayısı
BATCH_SIZE = 24           # Bir seferde kaç frame toplu işlenecek


class QRCodeScanner:
    """YouTube videolarındaki QR kodları tespit eden tarayıcı — optimize edilmiş."""

    def __init__(self, download_dir="downloads", snapshots_dir="static/snapshots"):
        self.download_dir = download_dir
        self.snapshots_dir = snapshots_dir
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(snapshots_dir, exist_ok=True)

    def is_playlist(self, url):
        """URL'nin bir playlist olup olmadığını kontrol et."""
        return 'list=' in url

    def extract_playlist(self, url, progress_callback=None):
        """Playlist'teki tüm video bilgilerini çıkar."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info is None:
                    raise Exception("Playlist bilgisi alınamadı")

                if info.get('_type') == 'playlist' or 'entries' in info:
                    entries = list(info.get('entries', []))
                    playlist_title = info.get('title', 'Bilinmeyen Playlist')

                    videos = []
                    for entry in entries:
                        if entry is None:
                            continue
                        video_url = entry.get('url') or entry.get('webpage_url', '')
                        if not video_url:
                            video_id = entry.get('id', '')
                            if video_id:
                                video_url = f'https://www.youtube.com/watch?v={video_id}'
                            else:
                                continue
                        elif not video_url.startswith('http'):
                            video_url = f'https://www.youtube.com/watch?v={video_url}'

                        videos.append({
                            'url': video_url,
                            'title': entry.get('title', 'Bilinmeyen Video'),
                            'duration': entry.get('duration', 0),
                            'id': entry.get('id', ''),
                        })

                    if progress_callback:
                        progress_callback('playlist', 0,
                            f"📋 Playlist: {playlist_title} — {len(videos)} video bulundu")

                    return {
                        'is_playlist': True,
                        'title': playlist_title,
                        'videos': videos,
                        'count': len(videos)
                    }
                else:
                    return {
                        'is_playlist': False,
                        'title': info.get('title', 'Tek Video'),
                        'videos': [{
                            'url': url,
                            'title': info.get('title', 'Bilinmeyen Video'),
                            'duration': info.get('duration', 0),
                            'id': info.get('id', ''),
                        }],
                        'count': 1
                    }
        except Exception as e:
            raise Exception(f"Playlist bilgisi alınamadı: {str(e)}")

    def download_video(self, url, progress_callback=None):
        """YouTube videosunu indir."""
        def progress_hook(d):
            if progress_callback and d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    pct = int((downloaded / total) * 100)
                    progress_callback('download', pct, f"Video indiriliyor... %{pct}")
            if progress_callback and d['status'] == 'finished':
                progress_callback('download', 100, "Video indirildi!")

        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id', 'unknown')
                title = info.get('title', 'Bilinmeyen Video')
                duration = info.get('duration', 0)

                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp4_file = base + '.mp4'
                if os.path.exists(mp4_file):
                    filename = mp4_file
                elif not os.path.exists(filename):
                    for f in os.listdir(self.download_dir):
                        if f.startswith(video_id):
                            filename = os.path.join(self.download_dir, f)
                            break

                return {
                    'path': filename,
                    'title': title,
                    'video_id': video_id,
                    'duration': duration
                }
        except Exception as e:
            raise Exception(f"Video indirme hatası: {str(e)}")

    def scan_video(self, video_path, skip_frames=3, progress_callback=None,
                   pause_event=None, stop_event=None):
        """
        Video dosyasını tara ve QR kodları tespit et.
        
        OPTİMİZASYONLAR:
        1. grab() ile atlanan frame'ler decode edilmiyor (RAM + CPU tasarrufu)
        2. Frame'ler SCAN_WIDTH'e küçültülüyor
        3. Batch halinde paralel tarama (ThreadPoolExecutor)
        4. Sıkı doğrulama ile yanlış pozitifler engelleniyor
        5. Pause/Stop kontrol noktaları
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Video açılamadı: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        found_qr_codes = []
        seen_data = set()
        frame_count = 0
        scanned_count = 0
        lock = threading.Lock()

        if progress_callback:
            frames_to_scan = total_frames // skip_frames
            progress_callback('scan', 0,
                f"⚡ Hızlı tarama başlıyor... ~{frames_to_scan} frame analiz edilecek")

        # Frame batch toplama ve paralel tarama
        batch = []  # [(frame_count, frame), ...]

        while True:
            # ===== KONTROL NOKTASI: Stop =====
            if stop_event and stop_event.is_set():
                break

            # ===== KONTROL NOKTASI: Pause =====
            if pause_event and pause_event.is_set():
                import time as _time
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        break
                    _time.sleep(0.15)
                if stop_event and stop_event.is_set():
                    break

            frame_count += 1

            # ===== OPTİMİZASYON 1: grab() vs read() =====
            # Atlanan frame'lerde sadece grab() çağrılır (decode yok = çok hızlı)
            if frame_count % skip_frames != 0:
                grabbed = cap.grab()
                if not grabbed:
                    break
                continue

            # Bu frame'i gerçekten oku (decode et)
            ret, frame = cap.read()
            if not ret:
                break

            scanned_count += 1

            # ===== OPTİMİZASYON 2: Frame küçültme =====
            frame_resized = self._resize_frame(frame)

            batch.append((frame_count, frame, frame_resized))

            # Batch dolduğunda veya ilerleme bildirimi zamanı
            if len(batch) >= BATCH_SIZE:
                self._process_batch(batch, fps, found_qr_codes, seen_data,
                                    lock, progress_callback)
                batch = []

            # İlerleme bildirimi
            if progress_callback and scanned_count % 30 == 0:
                pct = min(int((frame_count / total_frames) * 100), 99)
                current_time = frame_count / fps if fps > 0 else 0
                progress_callback('scan', pct,
                    f"Taranıyor... %{pct} | {scanned_count} frame tarandı | "
                    f"Süre: {self._format_time(current_time)} | "
                    f"Bulunan: {len(found_qr_codes)}")

        # Kalan batch'i işle
        if batch:
            self._process_batch(batch, fps, found_qr_codes, seen_data,
                                lock, progress_callback)

        cap.release()

        if progress_callback:
            progress_callback('scan', 100,
                f"Tarama tamamlandı! {scanned_count} frame tarandı, "
                f"{len(found_qr_codes)} QR kod bulundu.")

        return {
            'total_frames': total_frames,
            'scanned_frames': scanned_count,
            'fps': fps,
            'duration': duration,
            'duration_formatted': self._format_time(duration),
            'qr_codes': found_qr_codes
        }

    def _process_batch(self, batch, fps, found_qr_codes, seen_data,
                       lock, progress_callback):
        """Bir batch frame'i paralel olarak tara."""

        def scan_single(item):
            fc, frame_orig, frame_small = item
            qr_results = self._detect_qr_codes(frame_small)
            if qr_results:
                return (fc, frame_orig, qr_results)
            return None

        # Paralel tarama
        with ThreadPoolExecutor(max_workers=WORKER_THREADS) as executor:
            futures = {executor.submit(scan_single, item): item for item in batch}

            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue

                fc, frame_orig, qr_results = result

                for qr_data, qr_type, points_small in qr_results:
                    data_hash = hashlib.md5(qr_data.encode()).hexdigest()

                    with lock:
                        if data_hash in seen_data:
                            continue
                        seen_data.add(data_hash)

                    timestamp = fc / fps if fps > 0 else 0

                    # Snapshot'ı ORIJINAL çözünürlükte kaydet
                    # Noktaları orijinal boyuta ölçekle
                    points_orig = self._scale_points(
                        points_small, frame_orig.shape, SCAN_WIDTH)

                    snapshot_name = f"qr_{data_hash[:8]}_{fc}.jpg"
                    snapshot_path = os.path.join(self.snapshots_dir, snapshot_name)
                    self._save_snapshot(frame_orig, points_orig, snapshot_path)

                    with lock:
                        found_qr_codes.append({
                            'data': qr_data,
                            'type': qr_type,
                            'frame': fc,
                            'timestamp': timestamp,
                            'timestamp_formatted': self._format_time(timestamp),
                            'snapshot': f"/static/snapshots/{snapshot_name}"
                        })

                    if progress_callback:
                        progress_callback('found', len(found_qr_codes),
                            f"🎯 QR KOD BULUNDU! [{self._format_time(timestamp)}] "
                            f"— {qr_data[:80]}")

    def _resize_frame(self, frame):
        """Frame'i tarama için küçült. Orijinali bozmaz."""
        h, w = frame.shape[:2]
        if w <= SCAN_WIDTH:
            return frame
        scale = SCAN_WIDTH / w
        new_w = SCAN_WIDTH
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _scale_points(self, points_small, orig_shape, scan_width):
        """Küçültülmüş frame'deki noktaları orijinal boyuta ölçekle."""
        if points_small is None:
            return None
        orig_h, orig_w = orig_shape[:2]
        if orig_w <= scan_width:
            return points_small
        scale = orig_w / scan_width
        return [(int(x * scale), int(y * scale)) for x, y in points_small]

    def _detect_qr_codes(self, frame):
        """
        QR kod tespit et — SIKI DOĞRULAMA ile.
        
        Yanlış pozitif engelleme:
        - Sadece QRCODE tipi kabul edilir (barkod, EAN vs. reddedilir)
        - Minimum boyut kontrolü
        - Polygon şekil doğrulaması (4 köşe)
        - Boş veya çok kısa/uzun veri reddi
        """
        results = []
        seen_in_frame = set()

        # ===== Yöntem 1: pyzbar — SADECE QRCODE =====
        try:
            # ZBarSymbol.QRCODE filtresi ile sadece QR kodları tara
            decoded = pyzbar_decode(frame, symbols=[ZBarSymbol.QRCODE])
            for obj in decoded:
                if self._validate_detection(obj, frame.shape):
                    data = obj.data.decode('utf-8', errors='replace')
                    if data not in seen_in_frame:
                        seen_in_frame.add(data)
                        points = [(p.x, p.y) for p in obj.polygon] if obj.polygon else None
                        results.append((data, 'QRCODE', points))
        except Exception:
            pass

        # ===== Yöntem 2: OpenCV QRCodeDetector (zaten sadece QR) =====
        if not results:
            try:
                qr_detector = cv2.QRCodeDetector()
                retval, decoded_info, points_arr, _ = qr_detector.detectAndDecodeMulti(frame)
                if retval and decoded_info is not None:
                    for i, data in enumerate(decoded_info):
                        if data and len(data) >= MIN_QR_DATA_LEN and data not in seen_in_frame:
                            # OpenCV noktalarından boyut kontrol
                            if points_arr is not None:
                                pts = points_arr[i]
                                w = np.ptp(pts[:, 0])
                                h = np.ptp(pts[:, 1])
                                if w < MIN_QR_SIZE or h < MIN_QR_SIZE:
                                    continue
                            seen_in_frame.add(data)
                            pts_list = points_arr[i].astype(int).tolist() if points_arr is not None else None
                            results.append((data, 'QRCODE', pts_list))
            except Exception:
                pass

        # ===== Yöntem 3: Kontrast iyileştirme — sadece gerçekten zorluysa =====
        # Yalnızca ilk 2 yöntem başarısız olduğunda ve çıktı sıkı doğrulanır
        if not results:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)

                decoded = pyzbar_decode(enhanced, symbols=[ZBarSymbol.QRCODE])
                for obj in decoded:
                    if self._validate_detection(obj, frame.shape):
                        data = obj.data.decode('utf-8', errors='replace')
                        if data not in seen_in_frame:
                            seen_in_frame.add(data)
                            points = [(p.x, p.y) for p in obj.polygon] if obj.polygon else None
                            results.append((data, 'QRCODE', points))
            except Exception:
                pass

        return results

    def _validate_detection(self, obj, frame_shape):
        """
        Tespit edilen nesnenin gerçek bir QR kod olup olmadığını doğrula.
        Yanlış pozitifler burada filtrelenir.
        """
        # 1. Tip kontrolü — sadece QRCODE
        obj_type = obj.type if hasattr(obj, 'type') else ''
        if obj_type != 'QRCODE':
            return False

        # 2. Veri kontrolü
        try:
            data = obj.data.decode('utf-8', errors='replace')
        except Exception:
            return False

        if not data or len(data.strip()) < MIN_QR_DATA_LEN:
            return False
        if len(data) > MAX_QR_DATA_LEN:
            return False

        # 3. Polygon kontrolü — QR kodların 4 köşesi olmalı
        if obj.polygon:
            if len(obj.polygon) != 4:
                return False

            # Minimum boyut kontrolü
            xs = [p.x for p in obj.polygon]
            ys = [p.y for p in obj.polygon]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)

            if w < MIN_QR_SIZE or h < MIN_QR_SIZE:
                return False

            # En boy oranı kontrolü — QR kodlar kare olmalı (toleransla)
            if w > 0 and h > 0:
                aspect = max(w, h) / min(w, h)
                if aspect > 3.0:  # 3:1'den dar/geniş olamaz
                    return False

            # Frame dışı kontrol
            frame_h, frame_w = frame_shape[:2]
            if min(xs) < 0 or min(ys) < 0 or max(xs) > frame_w or max(ys) > frame_h:
                return False
        else:
            # Polygon yoksa reddet — konum bilgisi olmayan tespit güvenilir değil
            return False

        # 4. Veri kalitesi kontrolü — tamamen anlamsız karakterler reddet
        printable_ratio = sum(1 for c in data if c.isprintable()) / len(data)
        if printable_ratio < 0.5:
            return False

        return True

    def _save_snapshot(self, frame, points, path):
        """QR kod bulunan frame'in ekran görüntüsünü kaydet."""
        snapshot = frame.copy()

        if points:
            pts = np.array(points, dtype=np.int32)
            if len(pts.shape) == 2:
                cv2.polylines(snapshot, [pts], True, (0, 255, 0), 3)
                x, y, w, h = cv2.boundingRect(pts)
                padding = 15
                cv2.rectangle(snapshot,
                              (max(0, x - padding), max(0, y - padding)),
                              (x + w + padding, y + h + padding),
                              (0, 255, 0), 3)

        cv2.imwrite(path, snapshot, [cv2.IMWRITE_JPEG_QUALITY, 90])

    def _format_time(self, seconds):
        """Saniyeyi mm:ss formatına çevir."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def cleanup(self, video_path):
        """İndirilen video dosyasını sil."""
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception:
            pass
