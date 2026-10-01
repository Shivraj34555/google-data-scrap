@echo off
echo ==============================================
echo       Starting Google Maps Scraper
echo ==============================================

echo Automatically opening your web browser...
start http://127.0.0.1:8000

echo Starting Python Backend Server...
python manage.py runserver 8000

pause
