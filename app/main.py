import logging


from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

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
app = FastAPI(
    title="SKILLAB Projector Microservice",
    docs_url=None,
    redoc_url=None,
)
# Percorsi normali usati direttamente dal container:
# /projector/health, /projector/analyze-skills, ecc.
app.include_router(
    projector_router,
    prefix="/projector",
)

# Alias per Nginx, che rimuove il prefisso /projector.
# Non vengono duplicati nella documentazione OpenAPI.
app.include_router(
    projector_router,
    include_in_schema=False,
)


# Documentazione disponibile anche quando Nginx inoltra il prefisso /projector
# senza rimuoverlo.
@app.get("/projector/openapi.json", include_in_schema=False)
def projector_openapi():
    return app.openapi()


@app.get("/docs", include_in_schema=False)
@app.get("/projector/docs", include_in_schema=False)
def projector_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
@app.get("/projector/redoc", include_in_schema=False)
def projector_redoc():
    return get_redoc_html(
        openapi_url="openapi.json",
        title=f"{app.title} - ReDoc",
    )





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
