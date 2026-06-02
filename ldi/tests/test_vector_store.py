import pytest
import numpy as np
import tempfile
import os
import shutil
import gc

pytestmark = pytest.mark.requires_chromadb

from embeddings.vector_store import ClauseVectorStore


@pytest.fixture
def temp_persist_dir():
    path = tempfile.mkdtemp()
    yield path
    gc.collect()
    try:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    except PermissionError:
        pass


def test_add_and_search(temp_persist_dir):
    store = ClauseVectorStore(persist_directory=temp_persist_dir, collection_name="test_clauses")
    ids = ["c1", "c2"]
    texts = ["This is clause one.", "This is clause two."]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    metadatas = [{"clause_id": "c1", "section": "ART1"}, {"clause_id": "c2", "section": "ART2"}]
    store.add(ids, texts, embeddings, metadatas)
    results = store.search(np.array([1.0, 0.0], dtype=np.float32), k=2)
    assert results["ids"] is not None
    assert len(results["ids"][0]) == 2


def test_search_empty_collection(temp_persist_dir):
    store = ClauseVectorStore(persist_directory=temp_persist_dir, collection_name="empty_test")
    results = store.search(np.array([1.0, 0.0], dtype=np.float32), k=5)
    assert results["ids"] is not None
    assert len(results["ids"][0]) == 0


class TestAddValidation:
    def test_raises_on_list_length_mismatch(self, temp_persist_dir):
        store = ClauseVectorStore(persist_directory=temp_persist_dir, collection_name="val_test")
        with pytest.raises(ValueError):
            store.add(["a"], ["text1"], np.array([[1.0, 0.0]], dtype=np.float32), [])

    def test_raises_on_empty_lists(self, temp_persist_dir):
        store = ClauseVectorStore(persist_directory=temp_persist_dir, collection_name="val_test2")
        with pytest.raises(ValueError):
            store.add([], [], np.array([]), [])
