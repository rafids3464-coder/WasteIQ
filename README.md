# WASTE IQ — Smart Waste Management Platform

> **Production-ready** · Firebase-backed · AI-powered · Multilingual · Real-time

---

## Architecture

```
waste_iq/
├── backend/                    # FastAPI REST API
│   ├── main.py
│   ├── auth.py                 # Firebase Auth verification
│   ├── firestore_client.py     # Firestore SDK wrapper
│   ├── models.py               # Pydantic schemas
│   ├── waste_classifier.py     # MobileNetV2 classifier
│   ├── overflow_model.py       # RandomForest overflow predictor
│   ├── routing.py              # OpenRouteService routing
│   └── routers/
│       ├── auth_router.py
│       ├── bins_router.py
│       ├── classify_router.py
│       ├── complaints_router.py
│       ├── gamification_router.py
│       ├── overflow_router.py
│       ├── reports_router.py
│       └── routing_router.py
├── frontend/                   # Streamlit app
│   ├── app.py
│   ├── utils.py
│   ├── languages.py
│   ├── styles.css
│   └── pages/
│       ├── login.py
│       ├── household_dashboard.py
│       ├── municipal_dashboard.py
│       ├── driver_dashboard.py
│       ├── driver_route.py
│       ├── admin_dashboard.py
│       ├── classifier.py
│       ├── complaints.py
│       ├── rewards.py
│       ├── notifications.py
│       └── profile.py
├── requirements.txt
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
├── storage.rules
├── seed_firestore.py
└── .env.example
```

---

## Prerequisites

- Python 3.10+
- Firebase project with **Authentication**, **Firestore**, and **Storage** enabled
- [Firebase CLI](https://firebase.google.com/docs/cli): `npm install -g firebase-tools`
- Optional: [OpenRouteService API key](https://openrouteservice.org) for real driver routing

---

## Step 1 — Firebase Setup

1. Create a project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable **Email/Password** authentication
3. Create a **Firestore** database (Start in production mode)
4. Enable **Firebase Storage**
5. Download your **Service Account JSON**:  
   `Project Settings → Service accounts → Generate new private key`  
   → Save as `waste_iq/firebase_service_account.json`
6. Get your **Web App config**:  
   `Project Settings → General → Your apps → Add web app`  
   → Copy the config values

---

## Step 2 — Environment Variables

```bash
cd waste_iq
cp .env.example .env
# Edit .env and fill in all values
```

Required values:

| Variable | Where to get |
|---|---|
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to downloaded JSON key |
| `FIREBASE_API_KEY` | Firebase Web App config |
| `FIREBASE_AUTH_DOMAIN` | Firebase Web App config |
| `FIREBASE_PROJECT_ID` | Firebase Web App config |
| `FIREBASE_STORAGE_BUCKET` | Firebase Web App config |
| `ORS_API_KEY` | https://openrouteservice.org (free tier) |
| `BACKEND_URL` | `http://localhost:8000` for local dev |

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** On first run, MobileNetV2 weights (~14MB) are downloaded automatically.  
> On first run, the RandomForest overflow model is trained and saved as `overflow_model.pkl`.

---

## Step 4 — Deploy Firestore Rules & Indexes

```bash
cd waste_iq
firebase login
firebase use your-project-id
firebase deploy --only firestore
```

---

## Step 5 — Seed Demo Data

```bash
cd waste_iq
python seed_firestore.py
```

This creates 4 demo users, 8 bin locations (Kozhikode, Kerala), sample complaints, and waste logs.

**Demo credentials after seeding:**

| Role | Email | Password |
|---|---|---|
| Household | household@wasteiq.demo | demo1234 |
| Municipal | municipal@wasteiq.demo | demo1234 |
| Driver    | driver@wasteiq.demo    | demo1234 |
| Admin     | admin@wasteiq.demo     | demo1234 |

---

## Step 6 — Run Locally

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd waste_iq/backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd waste_iq/frontend
streamlit run app.py --server.port 8501
```

- Frontend: [http://localhost:8501](http://localhost:8501)
- Backend API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Render Free Tier Deployment

WASTE IQ is optimized to run exactly as a single Render Web Service on the Free Tier (512MB RAM), utilizing CPU-only PyTorch and an internal auto-started FastAPI subprocess.

1. **Push your code to GitHub** (Ensure `requirements.txt` and `.streamlit/config.toml` are committed).
2. Go to [Render.com](https://render.com) and create a new **Web Service**.
3. Connect your GitHub repository.
4. Set the following configuration:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0`
5. In the **Environment Variables** section, add your secrets:
   - `FIREBASE_API_KEY=...`
   - `FIREBASE_AUTH_DOMAIN=...`
   - `FIREBASE_PROJECT_ID=...`
   - `FIREBASE_STORAGE_BUCKET=...`
   - `GEMINI_API_KEY=...`
   - `BACKEND_URL=http://127.0.0.1:8000` *(Critical: This points the frontend to the internal auto-spawned FastAPI server)*
6. Click **Deploy Web Service**.

> **Note:** Free tier services spin down after 15 minutes of inactivity. It may take 1-2 minutes to wake back up. Once awake, YOLOv8-nano classification runs fully offline, meaning no Gemini API rate limits!

---

## API Reference

Base URL: `http://localhost:8000`  
All endpoints require `Authorization: Bearer <Firebase ID Token>`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System health check |
| POST | `/auth/signup` | Create user account |
| GET | `/auth/me` | Get current user profile |
| POST | `/classify/` | Upload image for AI classification |
| GET | `/classify/history` | Classification history |
| GET | `/bins/` | List bins |
| POST | `/bins/` | Create bin (municipal+) |
| POST | `/bins/{id}/collected` | Mark bin collected (driver) |
| POST | `/overflow/predict` | Predict overflow for one bin |
| POST | `/overflow/predict-batch` | Batch predictions for ward |
| GET | `/route/optimize` | Get driver's optimized route |
| POST | `/route/collect/{bin_id}` | Collect bin + recalculate route |
| GET | `/complaints/` | List complaints |
| POST | `/complaints/` | Submit complaint |
| PATCH | `/complaints/{id}/resolve` | Resolve complaint (municipal+) |
| GET | `/gamification/me` | My points & badges |
| GET | `/gamification/leaderboard` | Top users |
| GET | `/reports/city-summary` | City-wide stats (municipal+) |
| GET | `/reports/export-csv` | Download CSV (municipal+) |
| GET | `/reports/export-pdf` | Download PDF report |

---

## Features

| Feature | Tech |
|---|---|
| AI Waste Classification | TensorFlow MobileNetV2 + ImageNet |
| Overflow Prediction | scikit-learn RandomForest |
| Driver Routing | OpenRouteService API + Haversine fallback |
| Authentication | Firebase Auth (email/password + custom role claims) |
| Database | Firebase Firestore |
| Storage | Firebase Storage |
| Maps | Folium + CartoDB tiles |
| Charts | Plotly |
| Languages | English, Hindi, Malayalam, Tamil, Telugu |
| Gamification | Points, badges (Bronze/Silver/Gold), leaderboard |
| PDF Reports | ReportLab |
| Dark Mode | CSS variable theming |

---

## User Roles

| Role | Access |
|---|---|
| **Household** | Classify waste, submit complaints, view history, earn points |
| **Municipal** | View ward bins, resolve complaints, run overflow predictions |
| **Driver** | View assigned bins, optimized route, mark collections |
| **Admin** | Full system access, user management, city reports, all analytics |
