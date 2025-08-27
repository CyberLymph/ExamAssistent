# ExamAssistent

In order to install plugins from requirements run

'''bash
pip install -r requirements.txt 
'''


'''
FastAPI starten:

cd my-assistant-repo/fastapi_app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000


Django starten (neues Terminal):

cd my-assistant-repo/examassistant_ui
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 0.0.0.0:8001

'''