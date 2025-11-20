@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Starting Audio Server...
echo Access at http://localhost:8000 or http://<YOUR_IP>:8000
python server.py
pause
