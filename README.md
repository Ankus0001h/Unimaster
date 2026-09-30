<p align="center">
  <h1 align="center">🏛️ UniMaster — National Unified Material Master</h1>
  <p align="center"><strong>One Nation — One Material Code</strong></p>
  <p align="center">AI-Powered Common National Material Code (CNMC) Generation Platform for Central Public Sector Enterprises (CPSEs)</p>
</p>

---

## 📋 Problem Statement

India's **400+ Central Public Sector Enterprises (CPSEs)** each maintain their own material catalogs with different naming conventions, codes, and descriptions for identical items. This leads to:

- ❌ **Duplicate procurement** of the same material at different prices
- ❌ **No visibility** into inter-CPSE material availability
- ❌ **Inflated costs** due to fragmented, small-quantity purchasing
- ❌ **Zero standardization** across government enterprises

## 💡 Solution — UniMaster

UniMaster uses **AI/ML (NLP + Semantic Matching)** to automatically identify duplicate materials across CPSEs and assign a **Common National Material Code (CNMC)**, enabling:

- ✅ **National-level material deduplication** using Hybrid AI (TF-IDF + Sentence Transformers)
- ✅ **Unified catalog** with one code per unique material across all CPSEs
- ✅ **Inter-CPSE material transfer** — find and request materials from other enterprises
- ✅ **Demand aggregation** — bulk procurement at national scale for cost savings
- ✅ **Price transparency** — compare prices across CPSEs to detect overpricing
- ✅ **AI Auto-Approval** — configurable confidence thresholds for automated code approval

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    UniMaster Platform                     │
├──────────────┬───────────────────┬───────────────────────┤
│  CPSE Portal │  Admin Command    │    AI Engine           │
│  (Company)   │  Center (Govt)    │    (Backend)           │
├──────────────┼───────────────────┼───────────────────────┤
│ • Upload     │ • National        │ • Text Preprocessing   │
│   Materials  │   Analytics       │ • Attribute Extraction │
│ • View       │ • AI Match Engine │ • TF-IDF Vectorization │
│   Catalog    │ • CNMC Approvals  │ • Semantic Embeddings  │
│ • Track      │ • Auto-Approval   │ • Composite Scoring    │
│   Mappings   │   Settings        │ • Agglomerative        │
│ • Network    │ • Demand          │   Clustering           │
│   Search     │   Aggregation     │ • CNMC Code Generation │
│ • Material   │ • Audit Logs      │                        │
│   Transfers  │                   │                        │
│ • Demand     │                   │                        │
│   Submission │                   │                        │
└──────────────┴───────────────────┴───────────────────────┘
                         │
                    ┌────┴────┐
                    │ MongoDB │
                    └─────────┘
```

---

## 🧠 AI Pipeline

| Stage | Technology | Purpose |
|-------|-----------|---------|
| **Preprocessing** | Regex + Domain Abbreviations | Normalize descriptions (expand abbreviations, standardize units) |
| **Attribute Extraction** | Rule-based NLP | Extract dimensions, material type, grade, standard, etc. |
| **TF-IDF Vectorization** | scikit-learn (1–3 gram) | Capture keyword overlap and term frequency patterns |
| **Semantic Embeddings** | `all-MiniLM-L6-v2` (Sentence Transformers) | Capture contextual meaning beyond keywords |
| **Composite Scoring** | Weighted Formula | 50% Semantic + 40% Attribute + 10% Fuzzy matching |
| **Clustering** | Agglomerative Clustering | Group similar materials into CNMC clusters |
| **CNMC Generation** | MD5 Hashing (deterministic) | Generate consistent, reproducible national codes |
| **Auto-Approval** | Confidence Threshold | Auto-approve high-confidence clusters (configurable 70–100%) |

---

## 🚀 Features

### CPSE (Company) Dashboard
| Feature | Description |
|---------|-------------|
| 📤 **Material Upload** | Upload CSV/Excel files with auto schema mapping |
| 📋 **My Catalog** | View all uploaded materials with CNMC mappings and editable prices |
| 📊 **Analytics** | Company-specific statistics and charts |
| 🔗 **CNMC Mappings** | View local code → national code mappings |
| 🤖 **AI Suggestions** | See AI-proposed clusters with confidence scores |
| 🔍 **National Search** | Search materials across all CPSEs |
| 🚚 **Material Transfers** | Find materials in other CPSEs and request transfers |
| 📈 **Demand Aggregation** | Submit future material requirements for bulk procurement |
| 📝 **Audit Trail** | Full event log |

### Admin (Ministry) Command Center
| Feature | Description |
|---------|-------------|
| 📊 **National Analytics** | Total materials, clusters, approval stats, charts |
| 🧠 **AI Match Engine** | Run AI pipeline with real-time progress streaming (SSE) |
| ✅ **CNMC Approvals** | Review, approve, or reject proposed CNMC clusters |
| ⚙️ **AI Auto-Approval** | Configure confidence threshold for automatic approval |
| 📈 **Demand Aggregation** | View nationally aggregated procurement requirements |
| 📋 **Audit Logs** | Full governance trail of all admin actions |

---

## 📁 Project Structure

```
SIH Project/
├── app.py                    # Main Flask app + all REST API routes
├── config.py                 # Configuration (thresholds, weights, schema)
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (MONGO_URI, SECRET_KEY)
│
├── core_ai/                  # AI/ML Engine
│   ├── preprocessor.py       # Text normalization & cleaning
│   ├── attribute_extractor.py # Dimension, grade, material extraction
│   ├── vectorizer.py         # HybridVectorizer (TF-IDF + Sentence Transformers)
│   └── matcher.py            # MaterialMatcher (scoring + clustering)
│
├── services/                 # Business Logic
│   ├── schema_mapper.py      # Auto-map uploaded columns to standard schema
│   └── code_generator.py     # CNMC code generation (MD5 deterministic)
│
├── routes/                   # Flask Blueprints
│   ├── auth.py               # Login/Logout (CPSE + Admin)
│   ├── portal_cpse.py        # CPSE dashboard route
│   └── portal_admin.py       # Admin dashboard route
│
├── templates/                # Jinja2 HTML Templates
│   ├── home.html             # Landing page
│   ├── cpse/
│   │   └── dashboard.html    # CPSE portal (full SPA)
│   └── admin/
│       └── dashboard.html    # Admin command center (full SPA)
│
├── static/                   # CSS, JS, images
└── uploads/                  # Uploaded files (temporary)
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.10+**
- **MongoDB** (local or MongoDB Atlas)
- **pip** (Python package manager)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd "SIH Project"
```

### 2. Create Environment File
Create a `.env` file in the root:
```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
SECRET_KEY=your-secret-key-here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

The server starts at **http://localhost:5000**

---

## 🔐 Login Credentials

| Role | Access |
|------|--------|
| **CPSE User** | Login with company name (e.g., BHEL, SAIL, IOCL) |
| **Admin** | Login with admin credentials to access Command Center |

---

## 🗄️ MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `materials` | All uploaded material rows from all CPSEs |
| `uploads` | File upload metadata |
| `matches` | AI-detected duplicate pairs |
| `clusters` | Proposed/Approved/Rejected CNMC clusters |
| `audit_logs` | All approval, rejection, and settings change logs |
| `inter_cpse_transfers` | Material transfer requests between CPSEs |
| `demands` | Future demand submissions by CPSEs |
| `platform_settings` | Admin configurable settings (auto-approval threshold) |

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload material data (CSV/Excel) |
| `GET` | `/api/match` | Run AI engine (SSE streaming) |
| `GET` | `/api/recommendations` | Get all clusters and matches |
| `POST` | `/api/approve` | Approve/Reject a CNMC cluster |
| `POST` | `/api/search` | Search materials nationally |
| `GET` | `/api/analytics` | National analytics data |
| `GET/POST` | `/api/settings` | Get/Update platform settings |
| `GET` | `/api/network-availability/<code>` | Check material availability in other CPSEs |
| `POST` | `/api/request-transfer` | Request material from another CPSE |
| `POST` | `/api/submit-demand` | Submit future demand |
| `GET` | `/api/national-demand` | Get aggregated national demand |
| `POST` | `/api/update-price` | Update material price |
| `GET` | `/api/my-codes` | Autocomplete suggestions for codes |

---

## 🛡️ Key Design Decisions

1. **Deterministic CNMC Codes** — MD5 hash-based so re-running the engine generates the same codes
2. **Bulletproof Store Logic** — Only pending clusters are wiped on re-run; approved/rejected are untouched
3. **Auto-Approval with Audit** — All AI auto-approvals are fully logged for governance compliance
4. **Composite AI Scoring** — 50% Semantic + 40% Attribute + 10% Fuzzy for maximum accuracy
5. **URL Hash Routing** — Browser back/forward and reload preserves the current dashboard tab

---

## 👥 Team

**Smart India Hackathon (SIH) Project**

---

## 📄 License

This project is developed for the **Smart India Hackathon** under the problem statement for National Material Code standardization across CPSEs.
