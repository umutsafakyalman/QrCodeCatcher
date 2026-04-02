# 🎯 QR Code Catcher — YouTube Video QR Scanner

**QR Code Catcher** is an advanced, web-based Python tool that automatically detects and extracts **hidden QR codes** embedded within YouTube videos and playlists.

Featuring a modern "Glassmorphism" web UI and a high-performance scanning engine, it analyzes thousands of frames in seconds.

---

## ✨ Features

- **Playlist Support:** Provide a single link and easily queue hundreds of videos using the `yt-dlp` backend for continuous scanning.
- **Multithreaded High-Speed Scanning:** Simultaneously scans frames across 4 different threads for a single video.
- **Zero False Positives (Strict Validation):** Strict validation filters out standard barcodes (EAN/UPC) and random square pixels. It utilizes polygon point analysis and printable string ratio checks to eliminate fake results.
- **Real-Time UI & SSE:** Utilizes "Server-Sent Events" to display logs and captured QR codes on the frontend instantly. Supports live pausing (Pause) and stopping (Stop) during an active scan.
- **Battery and RAM Friendly:** Frame decoding overhead is bypassed for skipped frames using `cap.grab()`. The original 1080p frames are scaled down to 640px wide before being dispatched to `pyzbar` for scanning.
- **Multi-Language (i18n):** Includes English (EN) and Turkish (TR) UI support.

---

## 🚀 Installation

Ensure you have **Python 3.8+** and **FFmpeg** installed on your machine before running the project.

### 1. Install FFmpeg
Required by `yt-dlp` to download and convert video streams properly.
- **Windows:** Download from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add it to your Windows `PATH` environment variable.
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### 2. Clone and Setup
Pull the project to your local machine using the terminal:
```bash
git clone https://github.com/umutsafakyalman/QrCodeCatcher.git
cd QrCodeCatcher
```

Install the required Python packages:
```bash
pip install -r requirements.txt
```
*(Packages include: Flask, yt-dlp, opencv-python, pyzbar, Pillow, numpy)*

---

## 🕹️ How to Use

1. Run the `app.py` script located in the root directory:
```bash
python app.py
```
2. Open your web browser and navigate to `http://127.0.0.1:5000`.
3. Paste any **YouTube Video** or **Playlist** URL into the input field.
4. Select the **Scan Precision** (Skip Frames) setting:
   - *Very High (Every frame):* Scans slowly but can catch QR codes that appear for only 0.05 seconds.
   - *Normal (Every 3 frames - Recommended):* Scans at effectively ~10 fps for a 30 fps video. Provides a massive speed boost.
   - *Fast / Very Fast:* Choose this if you know the QR code stays on screen for a long duration (e.g., 3-4 seconds).
5. Click the **Start Scan** button.

The UI will automatically display the download percentage, live scanned frames, and the captured QR code data.

---

## 🛠️ How It Works (Technical Architecture)

The backend pipeline operates through the following stages:

1. **Connection & Download:** API requests are passed to `yt-dlp`. If it's a playlist, a queue is created. If it's a single video, it is temporarily downloaded at optimal resolution (e.g., 720p/1080p mp4) to the `downloads/` specific directory.
2. **Frame Selection:** OpenCV-Python is used to read the video. Proper decoding (`cap.read()`) is performed exclusively on the frames that meet the `skip_frames` interval constraint. Skipped frames are quickly bypassed (`cap.grab()`) without full decoding payload.
3. **Preprocessing & Resizing:** Fully parsed frames are minified to 640px maximal width. This significantly drops the heavy payload burden off the CPU's barcode detection capabilities.
4. **Parallel Detection (QR Detection):** The video is processed in batches (e.g., 24 frames/batch) sent through Python's `ThreadPoolExecutor`. Inside the worker threads:
    - Attempt a standard ZBar scan on the original frame.
    - If unreadable, aggressive CLAHE contrast boosting is applied to the image and it's tested again.
    - Extremely tiny detected objects are instantly rejected.
    - Data quality constraint checks run (eliminating noisy 20-character fake barcodes from random gradients).
5. **Reporting/Extraction:** Reusable QR codes are cropped natively from the original 1280px frame and exported as user-ready images (`.jpg` or `.webp`) to the `static/snapshots/` folder. The Flask server then emits Server-Sent Events straight to the front-end browser for live display.
6. **Cleanup Phase:** Upon scan completion or termination, the downloaded physical `.mp4` payloads inside `downloads/` are garbage-collected and permanently deleted to preserve disk space.

---

## License
Provided under the current repository's applicable usage terms. Feel free to open a Pull Request if you'd like to contribute.