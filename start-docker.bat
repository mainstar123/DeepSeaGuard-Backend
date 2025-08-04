@echo off
echo 🚀 Starting DeepSeaGuard with Docker...

REM Build and start all services
docker-compose up --build -d

echo ✅ Services started! Here's what's running:
echo.
echo 🌐 FastAPI App: http://localhost:8000
echo 📚 API Docs: http://localhost:8000/docs
echo 🔍 Celery Monitor: http://localhost:5555
echo.
echo 📊 Check service status:
docker-compose ps
echo.
echo 📝 View logs: docker-compose logs -f
echo 🛑 Stop services: docker-compose down
pause 