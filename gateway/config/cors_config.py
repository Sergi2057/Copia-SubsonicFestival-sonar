# gateway/config/cors_config.py
# CORS de toda la API: solo los orígenes del front-end configurados en CORS_ORIGENES
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import CORS_ORIGENES


def configurar_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGENES,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-Id"],
        expose_headers=["X-Total-Count", "Location", "X-Correlation-Id"],
    )
