#  ExamAssistent

A web platform for generating and optimizing exam questions with LLMs.
The project consists of:
- **FastAPI Backend** (analysis & interface to LLMs)
- **Django UI** (web interface for input and presentation)

---

##  Projektstruktur
ExamAssistent/
├─ fastapi_app/ # FastAPI Backend
│ └─ api.py
│ └─ client.py
│ └─ mistral.py
│ └─ .env # API-Keys und Settings
│ └─ requirements.txt

├─ examassistant_ui/ # Django UI
│ └─ manage.py
│ ├─  examassistant_ui/
│ ├─ chatui/
└─ README.md

---

##  Voraussetzungen
- Python **3.10+**
- Internetzugang (für Packages & APIs)
- API-Key für **Mistral**

---

##  Installation

**1. Create and activate a virtual environment**
#### macOS / Linux
bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
#### macOS / Linux

#### Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt // In order to install plugins from requirements
#### Windows (PowerShell)


**2. Create a .env File inside fastapi_app**
MISTRAL_API_KEY=your_mistral_key_here





**3. Starting FastAPI Backend**
   
#### Windows (PowerShell) / macOS & Linux
source .venv/bin/activate --> macOS & Linux
.venv\Scripts\Activate.ps1 --> Windows(PowerShell)

cd fastapi_app
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
#### Windows (PowerShell) / macOS & Linux

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc



**4. Starting Django/UI in a new terminal**
   
#### Windows (PowerShell) / macOS & Linux
source .venv/bin/activate --> macOS & Linux
.venv\Scripts\Activate.ps1 --> Windows(PowerShell)

cd examassistant_ui
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
#### Windows (PowerShell) / macOS & Linux

Django runs on → http://127.0.0.1:8001/
If you want to access the app from another device in your local network, use 0.0.0.0 instead of 127.0.0.1.

