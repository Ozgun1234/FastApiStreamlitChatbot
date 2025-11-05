## Hızlı Başlangıç

### 1. Geliştirme Ortamında Çalıştırma

#### Backend (FastAPI)

```sh
cd app/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

#### Frontend (Streamlit)

Başka bir terminalde:

```sh
cd app/frontend
pip install -r requirements.txt
streamlit run streamlit_app.py --server.port 8501
```

### 2. Docker ile Çalıştırma

#### Buildx ile Multi-Platform Image Oluşturma

Önce Docker Buildx builder'ı etkinleştir:

Backend için:

```sh
cd app/backend
docker buildx build -t ghcr.io/<your_github_account_name>/<docker_image_name>:<your_tag> .
```

Frontend için:

```sh
cd ../frontend
docker buildx build -t ghcr.io/<your_github_account_name>/<docker_image_name>:<your_tag> .
```

#### Docker Compose ile Başlatma

Build işleminin ardından proje kök dizininde:

```sh
docker-compose up --build
```

> Not: `docker-compose.yml` dosyanızın backend ve frontend servislerini doğru portlarla expose ettiğinden emin olun.

## Ortam Değişkenleri

- `BACKEND_URL`: Frontend'in backend'e bağlanacağı adres (varsayılan: `http://localhost:8002`).

## Temel Komutlar

- **Backend test etmek için:**  
  `curl http://localhost:8002/healthz`
- **Frontend'e erişmek için:**  
  Tarayıcıdan `http://localhost:8501` adresine gidin.

## Notlar

- `app/frontend/never_touch.py` ve `app/frontend/config.py` aynı zamanda `app/backend/core.py` dosyalarını değiştirmeyin.
- Geliştirme sırasında backend ve frontend'in aynı ağda olduğundan emin olun.
- PDF yükleme ve chat endpointleri mock (örnek) cevaplar döner.

## Katkı

PR ve issue'larınızı bekliyoruz!

---

**UcanbleHub Ekibi**