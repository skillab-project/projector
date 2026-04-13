import logging


from fastapi import FastAPI

from dotenv import load_dotenv

from app.api.routes.projector import router as projector_router

# Configurazione Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SKILLAB-Projector")

load_dotenv()
app = FastAPI(title="SKILLAB Projector Microservice")
app.include_router(projector_router)





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
