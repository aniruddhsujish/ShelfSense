from vectordb.client import create_title_index, get_client, create_collection
from embeddings.embedder import load_model
from db.ratings import init_db

client = get_client()
create_collection(client)
create_title_index(client)
model = load_model()
init_db()
