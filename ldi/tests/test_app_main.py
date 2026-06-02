from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestStubEndpoints:
    def test_ingest_endpoint(self):
        response = client.post("/ingest/")
        assert response.status_code == 200
        assert response.json() == {"message": "Standard ingestion active"}

    def test_chunk_endpoint(self):
        response = client.post("/chunk/")
        assert response.status_code == 200
        assert response.json() == {"message": "Chunking module active"}

    def test_ingest_multi_endpoint(self):
        response = client.post("/ingest-multi/")
        assert response.status_code == 200
        assert response.json() == {"message": "Multi-ingestion module active"}

    def test_chunk_multi_endpoint(self):
        response = client.post("/chunk-multi/")
        assert response.status_code == 200
        assert response.json() == {"message": "Multi-chunking module active"}

    def test_embed_multi_endpoint(self):
        response = client.post("/embed-multi/")
        assert response.status_code == 200
        assert response.json() == {"message": "Multi-embedding generation active"}

    def test_search_endpoint(self):
        response = client.post("/search/", json={"query": "test query"})
        assert response.status_code == 200
        assert response.json() == {"message": "Vector space retrieval active"}


class TestQueryHybrid:
    def test_query_hybrid_brightline(self):
        response = client.get("/query-hybrid/", params={"target_company": "Brightline", "query": "risk", "k": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["search_target"] == "Brightline"
        assert len(data["structural_network_risks"]) > 0
        assert len(data["semantic_vector_matches"]) > 0

    def test_query_hybrid_global_apex(self):
        response = client.get("/query-hybrid/", params={"target_company": "GLOBAL APEX", "query": "overage", "k": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data["structural_network_risks"]) > 0

    def test_query_hybrid_empty_results(self):
        response = client.get("/query-hybrid/", params={"target_company": "UNKNOWN ENTITY", "query": "test", "k": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data["structural_network_risks"]) == 0
        assert len(data["semantic_vector_matches"]) == 0
