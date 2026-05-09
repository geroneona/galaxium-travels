import uvicorn
from src.main import app, settings

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
