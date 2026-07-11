import uvicorn
import os
from pathlib import Path

# 切换工作目录到当前目录
os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    from config.settings import settings
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )