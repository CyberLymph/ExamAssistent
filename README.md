#  ExamAssistent

A web platform for generating and optimizing exam questions with LLMs.
The project consists of:
- **FastAPI Backend** (analysis & interface to LLMs)
- **Django UI** (web interface for input and presentation)

---

##  Projektstruktur
ExamAssistent/

├─ fastapi_app/ 

│ └─ api.py

│ └─ client.py

│ └─ mistral.py

│ └─ .env

│ └─ requirements.txt

├─ examassistant_ui/

│ └─ manage.py

│ ├─  examassistant_ui/

│ ├─ chatui/

└─ README.md



##  Voraussetzungen
- Python **3.10+**
- Internetzugang (für Packages & APIs)
- API-Key für **Mistral**


##  Installation

**1. Create and activate a virtual environment**
#### macOS / Linux
bash

python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

cd fastapi_app

pip install -r requirements.txt




---
#### Windows (PowerShell)

python -m venv .venv // Do this inside root

.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt // In order to install plugins from requirements


---
**2. Create a .env File inside fastapi_app**

MISTRAL_API_KEY=your_mistral_key_here





##  Starting the server
**3. Starting FastAPI Backend**
   
#### Windows (PowerShell) / macOS & Linux

source .venv/bin/activate --> macOS & Linux

.venv\Scripts\Activate.ps1 --> Windows(PowerShell)

cd fastapi_app

uvicorn api:app --host 127.0.0.1 --port 8000 --reload

---
Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc

---


**4. Starting Django/UI in a new terminal**
   
#### Windows (PowerShell) / macOS & Linux
source .venv/bin/activate --> macOS & Linux

.venv\Scripts\Activate.ps1 --> Windows(PowerShell)

cd examassistant_ui

python manage.py migrate

python manage.py runserver 127.0.0.1:8001

---
Django runs on → http://127.0.0.1:8001/

If you want to access the app from another device in your local network, use 0.0.0.0 instead of 127.0.0.1.

----------------------------------------------------------------------------------------------------------

In diesem Schritte kannst du dein Project auf ein mal starten (Frontend als auch Backend) --> Beide Server gleichzeitig laufen!

cd /Users/kholoudjlilaty/Desktop/SS2025/BP/GitHub/ExamAssistent

python -m fastapi_app.api

source ../.venv/bin/activate

chmod +x start_servers.sh

./start_servers.sh
