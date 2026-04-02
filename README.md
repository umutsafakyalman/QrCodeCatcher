# 🎯 QR Code Catcher — YouTube Video QR Scanner

**QR Code Catcher**, YouTube videoları ve oynatma listeleri (playlistler) içerisinde saklanmış olan **gizli QR kodları** otomatik olarak tespit edip ayıklayan web tabanlı gelişmiş bir Python aracıdır.

Modern "Glassmorphism" tasarıma sahip web arayüzü ve yüksek performanslı tarama motoru ile binlerce frame'i saniyeler içinde analiz eder.

---

## ✨ Özellikler

- **Oynatma Listesi (Playlist) Desteği:** Tek bir link vererek `yt-dlp` arka planıyla 100'lerce videoyu sıraya alabilir ve kesintisiz taratabilirsiniz.
- **Multithreading ile Yüksek Hız:** Video üzerinde 4 farklı thread ile eşzamanlı frame taraması yapılır.
- **Sıfır Yanlış Pozitif (Strict Validation):** Barkodlar (EAN/UPC), rasgele kare pikseller reddedilir. Polygon analizi ve printable string oranıyla sahte sonuçlar engellenir.
- **Gerçek Zamanlı UI & SSE:** Web arayüzünde "Server-Sent Events" ile her atılan log ve yakalanan QR kod anlık olarak gösterilir. Tarama yapılırken anlık duraklatma (Pause) ve durdurma (Stop) desteklenir.
- **Batarya ve RAM Dostu:** Atlanan frame'lerde `cap.grab()` kullanılarak "decode" masrafından kurtulunur ve tarama için orijinal 1080p frame'ler 640px genişliğine ölçeklenerek `pyzbar`a gönderilir.
- **Çoklu Dil (i18n):** Türkçe (TR) ve İngilizce (EN) dil destekleri.

---

## 🚀 Kurulum

Projeyi çalıştırmadan önce makinenizde **Python 3.8+** ve **FFmpeg**'in yüklü olması şarttır.

### 1. FFmpeg Yükleme
`yt-dlp`'nin videoları hatasız indirebilmesi ve format dönüştürmesi için gereklidir:
- **Windows:** [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) üzerinden indirip Windows `PATH` ortam değişkeninize ekleyin.
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### 2. Projeyi Klonlama ve Kurulum
Terminali açarak projeyi lokalinize çekin:
```bash
git clone https://github.com/umutsafakyalman/QrCodeCatcher.git
cd QrCodeCatcher
```

Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```
*(Paketler: Flask, yt-dlp, opencv-python, pyzbar, Pillow, numpy)*

---

## 🕹️ Nasıl Kullanılır?

1. Kök dizindeki `app.py` dosyasını çalıştırın:
```bash
python app.py
```
2. Tarayıcınızı açın ve `http://127.0.0.1:5000` adresine gidin.
3. Ekrana herhangi bir **YouTube Video** veya **Playlist** URL'sini yapıştırın.
4. **Tarama Hassasiyeti** (Skip Frames) ayarını seçin:
   - *Çok Yüksek (Her frame):* Tarama yavaş gerçekleşir ama 0.05 saniyelik kareleri bile yakalar.
   - *Normal (Her 3 frame - Önerilen):* 30 fps bir videoda yaklaşık 10 fps tarama yapar. Büyük hız kazancı.
   - *Hızlı / Çok Hızlı:* QR kod sadece videoda çok uzun (örn. 3-4 saniye) kalıyorsa seçilmelidir.
5. **Tarama Başlat** butonuna basın.

Arayüzde indirme yüzdesi, canlı taranan kareler ve yakalanan QR kod verileri belirecektir.

---

## 🛠️ Sistem Nasıl Çalışıyor? (Teknik Mimari)

Uygulamanın arka planı şu aşamalardan oluşur:

1. **Bağlantı & İndirme:** API'ye gelen istek `yt-dlp`'ye paslanır. Playlistse liste çıkartılır, tek video ise geçici olarak en uygun kalitede (ör. 720p/1080p mp4) indirilerek `downloads/` klasörüne atılır.
2. **Kare Seçimi (Frame Selection):** Opencv-Python kullanılarak video açılır. Sadece `skip_frames` periyoduna denk gelen frame'lerde asıl okuma (`cap.read()`) yapılır. Diğer boşluklardaki frame'ler tamamen decode edilmeden ibre atlatılır (`cap.grab()`).
3. **Ön İşlem & Küçültme:** Tam çözünürlüklü okunmuş frame, CPU üstündeki barkod arama yükünü dörte birine indirmek için maksimum eni 640px olacak şekilde küçültülür.
4. **Paralel Tespit (QR Detection):** 24 frame'lik batch'ler hazırlanır ve Python'un `ThreadPoolExecutor`'ına gönderilir. Threadler içinde:
    - Orijinal görüntüde ZBar algoritması aranır.
    - Bulunamazsa görüntünün konstrastı CLAHE tekniği kullanılarak patlatılır ve tekrar denenir.
    - Tespiti yapılan nesne minimum boyuttaysa (genişliği çok küçükse) reddedilir.
    - Tespit edilen barkod data kalitesi ölçülür (Gürültüyle gelen %20 karakterli çöp barkodlar elenir).
5. **Raporlama:** Geçerli kabul edilen QR kodu 1280px orijinal frame üzerinden kesilir (`crop`), web kullanımına hazır bir imaj dosyasına (`.webp` veya `.jpg`) çevrilerek `static/snapshots/` klasörüne çıkarılır. Flask sunucusu bu anı direkt olarak tarayıcıdaki Client'a fırlatır (SSE Teknolojisi).
6. **Temizlik:** Herhangi bir video tamamen taranıp bittiğinde, depolamayı sıkıştırmamak adına video `downloads/` içinden silinir.

---

## Lisans
Mevcut depo altındaki kullanım şartları geçerlidir. Katkıda bulunmak için pull request atabilirsiniz.