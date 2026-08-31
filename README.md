# TrueMark — Blockchain-Based Tamper-Proof Academic Credential Verification

**INTERNAL SIH 2026 · PS-03 · Team Practice Match**

> A hash-chain-backed platform where institutions issue digitally signed, tamper-proof academic credentials. Employers and verifiers can instantly validate authenticity via QR code or a public portal — without contacting the issuing institution.

---

## Problem Statement

Fake degrees, forged marksheets, and slow manual verification create trust and fraud issues for employers, universities, and government recruitment bodies. There is no fast, independent, and cryptographically secure way to verify an academic document today.

## Our Solution

TrueMark replaces manual background checks with a **cryptographic verification system**:

1. **Institutions** register on the platform and receive an **Ed25519 keypair**.
2. Credentials are issued (single or CSV upload), and each record is **SHA-256 hashed** and **digitally signed**.
3. Every credential's hash includes the **hash of the previous record**, forming an append-only **hash chain** per institution.
4. A **PDF certificate with an embedded QR code** is auto-generated for every credential.
5. Anyone can verify a credential on the **public verification portal** — the system recomputes the hash, walks the chain, and validates the signature.
6. If any field has been tampered with (even directly in the database), verification **instantly fails**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Python 3.10+, FastAPI |
| Database | PostgreSQL (Supabase) / SQLite (local dev) |
| ORM | SQLAlchemy 2.0 |
| Hashing | SHA-256 (`hashlib`) |
| Digital Signatures | Ed25519 (`PyNaCl`) |
| Authentication | JWT (HS256 via `python-jose`) |
| Password Hashing | PBKDF2-HMAC-SHA256 |
| QR Code Generation | `qrcode` + `Pillow` |
| PDF Certificate Generation | `ReportLab` |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Deployment (Backend) | Render (Gunicorn + Uvicorn) |
| Deployment (Frontend) | Vercel |

---

## Project Structure

```
PS3/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, CORS, router registration
│   │   ├── core/
│   │   │   ├── config.py            # Environment variables and settings
│   │   │   └── security.py          # JWT creation and verification (FastAPI dependency)
│   │   ├── crypto/
│   │   │   ├── hashing.py           # SHA-256 hash computation, genesis hash, chain helpers
│   │   │   └── signing.py           # Ed25519 keypair generation, sign, verify
│   │   ├── ledger/
│   │   │   ├── db.py                # SQLAlchemy engine, session factory, init_db()
│   │   │   ├── models.py            # ORM models: Institution, CredentialRecord, RevocationEvent
│   │   │   └── repository.py        # Data access layer for all three models
│   │   ├── routers/
│   │   │   ├── auth.py              # POST /auth/register, POST /auth/login
│   │   │   ├── issuance.py          # POST /credentials, POST /credentials/bulk, GET endpoints
│   │   │   ├── verification.py      # GET /verify/{credential_id}
│   │   │   └── revocation.py        # POST /revocations, GET /credentials/{id}/revocation-status
│   │   ├── schemas/
│   │   │   ├── credential.py        # Pydantic models for auth, issuance, and verification
│   │   │   └── revocation.py        # Pydantic models for revocation
│   │   ├── services/
│   │   │   ├── auth_service.py      # Registration (keypair gen) and login logic
│   │   │   ├── issuance_service.py  # Single and bulk issuance orchestration
│   │   │   ├── qr_service.py        # QR code PNG and PDF certificate generation
│   │   │   └── verification_service.py  # 4-check verification engine
│   │   └── tests/
│   │       ├── test_hashing.py      # Unit tests for hash determinism, tamper detection, chain linking
│   │       └── test_signing.py      # Unit tests for Ed25519 sign/verify, wrong-key rejection
│   ├── requirements.txt
│   ├── render.yaml                  # Render deployment configuration
│   └── .env.example                 # Environment variable template
│
├── frontend/
│   ├── index.html                   # Landing page (public)
│   ├── login.html                   # Institution login/register page
│   ├── dashboard.html               # Institution dashboard (issue, bulk upload, manage, revoke)
│   ├── verify.html                  # Public verification portal (Enter ID / Scan QR / Upload Document)
│   ├── verify-result.html           # Verification result page (VALID / TAMPERED / REVOKED / NOT FOUND)
│   └── assets/
│       ├── css/                     # Stylesheets (base, layout, components, page-specific)
│       ├── js/
│       │   ├── auth.js              # Login and registration logic
│       │   ├── dashboard.js         # Dashboard: issuance, bulk CSV, credential listing, revocation
│       │   └── script.js            # Landing page interactions
│       └── images/
│
├── .gitignore
└── README.md
```

---

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Register a new institution. Generates an Ed25519 keypair. |
| `POST` | `/auth/login` | No | Authenticate and receive a JWT access token. |

### Credential Issuance (`/credentials`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/credentials` | JWT | Issue a single credential (hash, sign, store, generate QR). |
| `POST` | `/credentials/bulk` | JWT | Bulk issue from a CSV file. Validates all rows before issuing. |
| `GET` | `/credentials/mine` | JWT | List all credentials issued by the logged-in institution. |
| `GET` | `/credentials/{id}/qr` | No | Download the QR code PNG for a credential. |
| `GET` | `/credentials/{id}/certificate` | No | Download the PDF certificate for a credential. |

### Verification (`/verify`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/verify/{credential_id}` | No | Public endpoint. Runs 4 independent checks and returns the result. |

### Revocation (`/revocations`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/revocations` | JWT | Revoke a credential (append-only, original record is never modified). |
| `GET` | `/credentials/{id}/revocation-status` | No | Public endpoint to check if a credential has been revoked. |

---

## Verification Engine — 4 Independent Checks

When `GET /verify/{credential_id}` is called, the backend performs:

| # | Check | What It Does | Detects |
|---|---|---|---|
| 1 | **Hash Validity** | Recomputes SHA-256 hash from stored fields and compares to `record_hash`. | Direct field tampering in the database. |
| 2 | **Chain Integrity** | Walks the full hash chain from genesis (`"0" × 64`) to the target credential, verifying each link. | Insertion, deletion, or reordering of records. |
| 3 | **Signature Validity** | Verifies the Ed25519 signature using the institution's public key. | Forged credentials or hash-rewrite attacks. |
| 4 | **Revocation Status** | Checks if a revocation event exists for this credential. | Credentials revoked due to error or fraud. |

**Final status returned:**
- `VALID` — all checks pass, no revocation.
- `TAMPERED` — hash or chain integrity check failed.
- `REVOKED` — credential was explicitly revoked by the institution.
- `NOT_FOUND` — credential ID does not exist in the ledger.

---

## Frontend Pages

| Page | URL | Description |
|---|---|---|
| **Landing Page** | `index.html` | Public-facing homepage with animated splash screen. |
| **Login / Register** | `login.html` | Institution authentication with email and password. |
| **Dashboard** | `dashboard.html` | Authenticated institution panel: issue single credentials, bulk CSV upload, view issued credentials, revoke credentials. |
| **Verification Portal** | `verify.html` | Public portal with 3 verification methods: Enter ID, Scan QR (camera), Upload Document (JSON/PDF/Image). |
| **Verification Result** | `verify-result.html` | Displays the verification outcome with credential details and cryptographic evidence. |

### Verification Portal — 3 Methods

| Method | Input | How It Works |
|---|---|---|
| **Enter ID** | Credential UUID (text input) | Directly queries the verification API with the entered ID. |
| **Scan QR** | Camera (live scan) | Uses `html5-qrcode` to scan a QR code from a physical/digital certificate, extracts the UUID, and verifies. |
| **Upload Document** | `.json`, `.pdf`, or image file | **JSON:** Parses the file for an `id` or `credential_id` field. **PDF:** Renders pages via `pdf.js` and scans for QR codes. **Image:** Scans for embedded QR codes. |

---

## Database Schema

### `institutions`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique institution identifier. |
| `name` | Text | Institution name. |
| `email` | Text (Unique) | Login email. |
| `password_hash` | Text | PBKDF2-HMAC-SHA256 hashed password. |
| `public_key` | Text | Ed25519 public key (hex). |
| `private_key_path` | Text | Ed25519 private key (hex, stored server-side). |
| `field_schema` | JSON | Optional custom field definitions for this institution. |
| `created_at` | DateTime | Registration timestamp. |

### `credential_records`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique credential identifier (used in QR codes and verification). |
| `institution_id` | UUID (FK) | Issuing institution. |
| `student_name` | Text | Student's full name. |
| `roll_no` | Text | Roll number. |
| `degree` | Text | Degree name. |
| `cgpa` | Text | CGPA (optional). |
| `issue_date` | Date | Date of issuance. |
| `custom_fields` | JSON | Institution-defined extra fields (optional). |
| `prev_hash` | Text | SHA-256 hash of the previous credential in the chain. |
| `record_hash` | Text | SHA-256 hash of this credential's data + `prev_hash`. |
| `signature` | Text | Ed25519 signature of `record_hash`. |
| `qr_payload` | Text | URL embedded in the QR code (`/verify/{id}`). |
| `created_at` | DateTime | Record creation timestamp. |

### `revocation_events`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique revocation event identifier. |
| `credential_id` | UUID (FK) | The credential being revoked. |
| `institution_id` | UUID (FK) | The institution performing the revocation. |
| `reason` | Text | Reason for revocation. |
| `prev_hash` | Text | Previous hash in the revocation chain. |
| `record_hash` | Text | SHA-256 hash of this revocation event. |
| `signature` | Text | Ed25519 signature of the revocation hash. |
| `created_at` | DateTime | Revocation timestamp. |

---

## How to Run Locally

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite for local development)

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your database URL and secrets

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive API docs are at `http://localhost:8000/docs`.

### Frontend Setup

Open `frontend/index.html` directly in a browser, or serve with any static file server:

```bash
cd frontend
python -m http.server 5500
```

The frontend automatically detects `localhost` and connects to `http://localhost:8000` for API calls.

### Run Tests

```bash
cd backend
pytest app/tests/ -v
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — (required) |
| `SECRET_KEY` | Secret for auth service crypto operations | `sih2026-super-secret-key` |
| `JWT_SECRET` | Secret key for JWT signing | `change-me-in-production-for-jwt` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRY_MINUTES` | Token expiry in minutes | `60` |
| `BASE_URL` | Backend API base URL (used in QR payloads) | `https://truemark-backend-sih.onrender.com` |
| `FRONTEND_URL` | Allowed CORS origin | `https://truemark-one.vercel.app` |

---

## Deployment

- **Backend:** Deployed on [Render](https://render.com) using `render.yaml`. Runs Gunicorn with Uvicorn workers.
- **Frontend:** Deployed on [Vercel](https://vercel.com) as a static site.

---

## Unit Tests

| Test File | Covers |
|---|---|
| `test_hashing.py` | Hash determinism, tamper detection (single field edit breaks hash), chain linking (different `prev_hash` produces different output), genesis hash detection, field-order independence. |
| `test_signing.py` | Keypair generation, valid signature verification, wrong-key rejection, tampered-hash rejection, garbage input handling, invalid private key rejection. |
