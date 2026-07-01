from qdrant_client import QdrantClient, models

LOCAL_PATH = "./qdrant_storage"
CLOUD_URL = (
    "https://5f86662d-6056-4a0f-8f67-b45613ecbc09.us-east-1-1.aws.cloud.qdrant.io"
)
CLOUD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MDE0ZGI2ZTktNWUyNy00MjZjLTlmYTUtOWM5NGM4NTFlYTVlIn0.npu3nv3dXIk35M09eDolNm-KdLtFLAPsf75qFEHhHNw"
COLLECTION = "books"
BATCH_SIZE = 100

local = QdrantClient(path=LOCAL_PATH)
cloud = QdrantClient(url=CLOUD_URL, api_key=CLOUD_API_KEY)

# Create collection on cloud if it doesn't exist
existing = [c.name for c in cloud.get_collections().collections]
if COLLECTION not in existing:
    cloud.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    print("Created collection on cloud")

total = local.get_collection(COLLECTION).points_count
print(f"Migrating {total} points...")

offset = None
migrated = 0

while True:
    points, next_offset = local.scroll(
        collection_name=COLLECTION,
        limit=BATCH_SIZE,
        offset=offset,
        with_vectors=True,
        with_payload=True,
    )

    if not points:
        break

    cloud.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(id=p.id, vector=p.vector, payload=p.payload)
            for p in points
        ],
    )

    migrated += len(points)
    print(f"Migrated {migrated}/ total")

    if next_offset is None:
        break
    offset = next_offset

print("Migration complete.")
