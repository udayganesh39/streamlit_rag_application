import json
from pathlib import Path
from types import SimpleNamespace

import main


def test_scan_data_directory_filters_supported_types(tmp_path, monkeypatch):
    for filename in ("report.pdf", "notes.txt", "draft.docx", "ignore.md"):
        (tmp_path / filename).write_text("sample", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))

    file_map = main.scan_data_directory()

    assert sorted(file_map.keys()) == ["docx", "pdf", "txt"]
    assert [path.name for path in file_map["pdf"]] == ["report.pdf"]


def test_load_docs_uses_matching_loader(monkeypatch):
    loaded_paths = []

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            loaded_paths.append(self.file_path)
            return [self.file_path]

    monkeypatch.setattr(main, "PyPDFLoader", FakeLoader)
    monkeypatch.setattr(main, "TextLoader", FakeLoader)
    monkeypatch.setattr(main, "UnstructuredWordDocumentLoader", FakeLoader)

    docs = main.load_docs("pdf", ["a.pdf", "b.pdf"])

    assert docs == ["a.pdf", "b.pdf"]
    assert loaded_paths == ["a.pdf", "b.pdf"]


def test_build_or_load_faiss_creates_new_index(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "INDEX_BASE_DIR", str(tmp_path))
    monkeypatch.setattr(main, "get_gemini_embeddings", lambda: "embeddings")
    monkeypatch.setattr(main, "load_docs", lambda *_args, **_kwargs: ["doc-a"])

    class FakeIndex:
        def __init__(self):
            self.saved_to = None
            self.added_docs = []

        def add_documents(self, docs):
            self.added_docs.extend(docs)

        def save_local(self, path):
            self.saved_to = path

    class FakeFaiss:
        created = None

        @classmethod
        def from_documents(cls, docs, embeddings):
            cls.created = FakeIndex()
            cls.created.added_docs.extend(docs)
            cls.embeddings = embeddings
            return cls.created

        @staticmethod
        def load_local(*_args, **_kwargs):
            raise AssertionError("load_local should not be called for a new index")

    monkeypatch.setattr(main, "FAISS", FakeFaiss)

    file_path = tmp_path / "alpha.pdf"
    file_path.write_text("content", encoding="utf-8")

    index = main.build_or_load_faiss("pdf", [file_path])
    meta_path = tmp_path / "pdf_indexed.json"

    assert index is FakeFaiss.created
    assert index.saved_to == str(tmp_path / "pdf_index")
    assert FakeFaiss.embeddings == "embeddings"
    assert json.loads(meta_path.read_text(encoding="utf-8")) == [str(file_path.resolve())]


def test_build_or_load_faiss_loads_existing_index_when_no_new_files(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "INDEX_BASE_DIR", str(tmp_path))
    monkeypatch.setattr(main, "get_gemini_embeddings", lambda: "embeddings")

    file_path = tmp_path / "alpha.pdf"
    file_path.write_text("content", encoding="utf-8")

    index_dir = tmp_path / "pdf_index"
    index_dir.mkdir()
    meta_path = tmp_path / "pdf_indexed.json"
    meta_path.write_text(json.dumps([str(file_path.resolve())]), encoding="utf-8")

    expected_index = object()

    class FakeFaiss:
        @staticmethod
        def load_local(path, embeddings, allow_dangerous_deserialization):
            assert path == str(index_dir)
            assert embeddings == "embeddings"
            assert allow_dangerous_deserialization is True
            return expected_index

    monkeypatch.setattr(main, "FAISS", FakeFaiss)

    index = main.build_or_load_faiss("pdf", [file_path])

    assert index is expected_index


def test_retrieve_all_sources_skips_missing_stores():
    class FakeStore:
        def __init__(self, docs):
            self.docs = docs

        def similarity_search(self, query, k=2):
            assert query == "hello"
            assert k == 3
            return self.docs

    docs = main.retrieve_all_sources(
        "hello",
        {"pdf": FakeStore(["doc-1"]), "txt": None, "docx": FakeStore(["doc-2"])},
        k=3,
    )

    assert docs == ["doc-1", "doc-2"]


def test_main_logic_returns_none_when_no_supported_files(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "INDEX_BASE_DIR", str(tmp_path / "indexes"))
    monkeypatch.setattr(main, "scan_data_directory", lambda: {})

    assert main.main_logic("question") is None


def test_main_logic_builds_context_and_returns_llm_response(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "INDEX_BASE_DIR", str(tmp_path / "indexes"))
    monkeypatch.setattr(main, "scan_data_directory", lambda: {"pdf": [Path("sample.pdf")]})
    monkeypatch.setattr(main, "build_or_load_faiss", lambda *_args, **_kwargs: "store")

    docs = [
        SimpleNamespace(page_content="First chunk"),
        SimpleNamespace(page_content="Second chunk"),
    ]
    monkeypatch.setattr(main, "retrieve_all_sources", lambda *_args, **_kwargs: docs)

    class FakeLlm:
        def __init__(self):
            self.prompt = None

        def invoke(self, prompt):
            self.prompt = prompt
            return SimpleNamespace(content="final answer")

    fake_llm = FakeLlm()
    monkeypatch.setattr(main, "get_gemini_llm", lambda: fake_llm)

    answer = main.main_logic("What happened?")

    assert answer == "final answer"
    assert "First chunk\nSecond chunk" in fake_llm.prompt
    assert "Question: What happened?" in fake_llm.prompt
