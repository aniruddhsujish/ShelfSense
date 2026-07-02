from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from vectordb.client import get_client, create_collection
from embeddings.embedder import load_model
from db.ratings import init_db
from api.routes.books import router
from api.dependencies import client, model

load_dotenv()

app = FastAPI(title="Book Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://shelf-sense-pied.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
