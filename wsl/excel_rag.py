"""
excel_rag.py — entry point CLI (wrapper fino).

Mantido para compatibilidade com docker-compose e chamadas de subprocess.
Toda a lógica foi movida para interfaces/cli/commands.py.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env antes de qualquer import de módulo interno
load_dotenv(dotenv_path=Path(__file__).with_name("settings.env"), override=False)
load_dotenv(override=False)

from interfaces.cli.commands import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())


# ─────────────────────────────────────────────────────────────────────────────
# LEGADO: classes mantidas para não quebrar imports externos já existentes.
# Use os módulos em infrastructure/ e application/ para código novo.
# ─────────────────────────────────────────────────────────────────────────────

import os, re, requests  # noqa: E401, F401
import pandas as pd  # noqa: F401
import chromadb  # noqa: F401
from chromadb.config import Settings  # noqa: F401
from typing import List  # noqa: F401
from pypdf import PdfReader  # noqa: F401
from docx import Document  # noqa: F401
from requests.adapters import HTTPAdapter  # noqa: F401
from urllib3.util.retry import Retry  # noqa: F401


# ---- Embeddings locais via Sentence-Transformers (sem Ollama) ----
class LocalHFEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        # quando for embedar docs na ingestão:
        batch_size = int(os.getenv("EMBED_BATCH", "64"))
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            vecs = self.model.encode(
                batch,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            embeddings.extend(v.tolist() for v in vecs)
        return embeddings


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/api/embeddings"
        outs = []
        for t in texts:
            r = requests.post(url, json={"model": self.model, "input": t}, timeout=120)
            if r.status_code == 404:
                raise RuntimeError(f"[404] {url} — verifique se o modelo '{self.model}' foi baixado e se o Ollama está ativo.")
            r.raise_for_status()
            data = r.json()
            emb = data.get("embedding")
            if not emb:
                raise RuntimeError(f"Resposta inesperada do Ollama: {data}")
            outs.append(emb)
        return outs


class OllamaLLM:
    """
    LLM via Ollama com opções de performance.
    Lê envs:
      - NUM_THREADS        (ex.: 8)
      - NUM_CTX            (ex.: 1024)
      - MAX_TOKENS         (fallback quando max_tokens não for passado)
      - TEMP               (temperatura: 0.2 recomendado p/ respostas objetivas)
      - TOP_P              (top-p: 0.9)
      - REPEAT_PENALTY     (1.05–1.2; 1.1 padrão)
      - OLLAMA_CONNECT_TIMEOUT (padrão 10s)
      - OLLAMA_READ_TIMEOUT    (padrão 1200s)
    """
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model

        def _int(env, default):
            try: return int(os.getenv(env, str(default)))
            except ValueError: return default

        def _float(env, default):
            try: return float(os.getenv(env, str(default)))
            except ValueError: return default

        self.num_threads     = _int("NUM_THREADS", 0)      # 0 = deixar Ollama decidir
        self.num_ctx         = _int("NUM_CTX", 1024)       # contexto menor ajuda na velocidade
        self.env_max_tokens  = _int("MAX_TOKENS", 96)      # fallback se não for passado na chamada
        self.temperature     = _float("TEMP", 0.2)
        self.top_p           = _float("TOP_P", 0.9)
        self.repeat_penalty  = _float("REPEAT_PENALTY", 1.1)

        # timeouts e sessão com retry
        self.connect_timeout = _int("OLLAMA_CONNECT_TIMEOUT", 10)
        self.read_timeout    = _int("OLLAMA_READ_TIMEOUT", 1200)

        self.session = requests.Session()
        self.session.mount(
            "http://",
            HTTPAdapter(max_retries=Retry(
                total=2, backoff_factor=2,
                status_forcelist=[502, 503, 504],
                allowed_methods=frozenset(["POST", "GET"])
            ))
        )
        self.session.mount(
            "https://",
            HTTPAdapter(max_retries=Retry(
                total=2, backoff_factor=2,
                status_forcelist=[502, 503, 504],
                allowed_methods=frozenset(["POST", "GET"])
            ))
        )

    def _post(self, url: str, payload: dict):
        return self.session.post(url, json=payload, timeout=(self.connect_timeout, self.read_timeout))

    def warmup(self):
        """Chamada curta para carregar o modelo antes da primeira geração."""
        try:
            gen_url = f"{self.base_url}/api/generate"
            payload = {"model": self.model, "prompt": "ok", "options": {"num_predict": 1}, "stream": False}
            self._post(gen_url, payload)
        except Exception:
            pass  # warmup é best-effort

    def generate(self, prompt: str, max_tokens: int = None) -> str:
        base = self.base_url.rstrip('/')
        num_predict = max_tokens if (isinstance(max_tokens, int) and max_tokens > 0) else self.env_max_tokens

        options = {
            "num_predict":    num_predict,
            "num_ctx":        self.num_ctx,
            "temperature":    self.temperature,
            "top_p":          self.top_p,
            "repeat_penalty": self.repeat_penalty,
        }
        if self.num_threads > 0:
            options["num_thread"] = self.num_threads  # acelera no CPU

        # 1) tenta /api/generate
        gen_url = f"{base}/api/generate"
        payload_gen = {"model": self.model, "prompt": prompt, "options": options, "stream": False}
        r = self._post(gen_url, payload_gen)

        if r.status_code == 404:
            # 2) fallback para /api/chat
            chat_url = f"{base}/api/chat"
            payload_chat = {
                "model":   self.model,
                "messages": [
                    {"role": "system", "content": "Responda de forma concisa e objetiva."},
                    {"role": "user",   "content": prompt}
                ],
                "options": options,
                "stream":  False
            }
            r2 = self._post(chat_url, payload_chat)
            if not r2.ok:
                raise requests.HTTPError(f"[Ollama /api/chat {r2.status_code}] {r2.text}", response=r2)
            data = r2.json()
            msg = (data.get("message") or {}).get("content", "")
            return (msg or "").strip()

        if not r.ok:
            raise requests.HTTPError(f"[Ollama /api/generate {r.status_code}] {r.text}", response=r)

        data = r.json()
        return (data.get("response") or "").strip()


class LocalRAG:
    def __init__(self, persist_dir: str, embedder: LocalHFEmbedder, top_k: int = 6):
        self.embedder = embedder
        self.top_k = max(1, int(top_k))
        # Desabilita telemetria para evitar erros "Failed to send telemetry ..."
        self.client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            is_persistent=True,
            anonymized_telemetry=False
        ))
        collection_name = os.getenv("COLLECTION_NAME", "knowledge_base")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    @staticmethod
    def _read_file(path: Path):
        text_items = []
        suffix = path.suffix.lower()
        try:
            if suffix in [".txt", ".md"]:
                text = path.read_text(encoding="utf-8", errors="ignore")
                text_items.append({"source": str(path), "text": text})
            elif suffix == ".pdf":
                reader = PdfReader(str(path))
                pages = []
                for p in reader.pages:
                    try:
                        pages.append(p.extract_text() or "")
                    except Exception:
                        continue
                text = "\n".join(pages)
                if text.strip():
                    text_items.append({"source": str(path), "text": text})
            elif suffix == ".docx":
                doc = Document(str(path))
                paras = [para.text for para in doc.paragraphs]
                text = "\n".join(paras)
                if text.strip():
                    text_items.append({"source": str(path), "text": text})
            elif suffix in [".csv"]:
                df = pd.read_csv(path, encoding="utf-8", errors="ignore")
                text_items.append({"source": str(path), "text": df.to_csv(index=False)})
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(path)
                text_items.append({"source": str(path), "text": df.to_csv(index=False)})
        except Exception as e:
            print(f"[WARN] Falha ao ler {path}: {e}")
        return text_items

    def ingest_folder(self, folder: Path):
        docs, metas, ids = [], [], []
        for p in folder.rglob("*"):
            if p.is_file():
                for item in self._read_file(p):
                    text = re.sub(r"\s+", " ", item["text"]).strip()
                    if not text:
                        continue
                    docs.append(text)
                    metas.append({"source": item["source"]})
                    ids.append(f"{item['source']}#{abs(hash(text))}")
        if not docs:
            print("[INGEST] Nenhum documento legível encontrado.")
            return
        print(f"[INGEST] Gerando embeddings para {len(docs)} chunks...")
        embeds = self.embedder.embed(docs)
        self.collection.add(documents=docs, metadatas=metas, ids=ids, embeddings=embeds)
        print("[INGEST] Concluído.")

    def query(self, question: str):
        # Limita n_results ao tamanho do índice para evitar warnings
        try:
            total = self.collection.count()
        except Exception:
            total = None
        if not total:
            return []

        q_emb = self.embedder.embed([question])[0]
        n_results = min(self.top_k * 2, int(total))

        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        # 2.1) filtro de similaridade mínima (descarta ruído)
        MIN_SIM = float(os.getenv("MIN_SIM", "0.35"))  # ajuste fino
        # chroma retorna "distância" (menor é melhor); convertemos para sim ~ 1 - dist aproximado
        pairs = []
        for doc, meta, dist in zip(docs, metas, dists):
            sim = 1.0 - float(dist)
            if sim >= MIN_SIM and (doc or "").strip():
                pairs.append((sim, doc, meta))

        # 2.2) reranking opcional com cross-encoder (melhora muito a precisão)
        try:
            from sentence_transformers import CrossEncoder
            reranker_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            ce = CrossEncoder(reranker_name)
            pairs_for_ce = [(question, d) for _, d, _ in pairs]
            scores = ce.predict(pairs_for_ce)
            pairs = [(float(s), d, m) for s, (_, d, m) in zip(scores, pairs)]
            pairs.sort(key=lambda x: x[0], reverse=True)
        except Exception:
            pairs.sort(key=lambda x: x[0], reverse=True)

        # 2.3) escolhe os k finais
        k = max(1, int(self.top_k))
        out = []
        for _, d, m in pairs[:k]:
            out.append({"text": d, "source": m.get("source", "")})
        return out


TEMPLATE = (
    "Responda em português, de forma objetiva (máx. 5 linhas). "
    "Use SOMENTE as informações do CONTEXTO. "
    "Se estiver ausente, responda literalmente: 'Informação não encontrada nos documentos internos.'\n\n"
    "[PERGUNTA]\n{question}\n\n"
    "[CONTEXTO]\n{context}\n\n"
    "Inclua as fontes no formato [Fonte N].\n"
    "Resposta:"
)

def build_context(snippets):
    # reduz cada trecho para evitar estourar num_ctx
    MAX_PER_SNIPPET = 1200
    blocos = []
    for i, s in enumerate(snippets, 1):
        t = (s['text'] or "").strip()
        if len(t) > MAX_PER_SNIPPET:
            t = t[:MAX_PER_SNIPPET] + "…"
        blocos.append(f"[Fonte {i}: {s.get('source','')}]\n{t}")
    return "\n\n".join(blocos)


def process_excel(input_xlsx: Path, output_xlsx: Path, sheet: str, q_col: str, a_col: str,
                  rag: LocalRAG, llm: OllamaLLM, max_tokens: int):
    df = pd.read_excel(input_xlsx, sheet_name=sheet)
    if a_col not in df.columns:
        df[a_col] = ""
    # garante que a coluna de respostas aceita strings
    df[a_col] = df[a_col].astype(object)
    total = len(df)
    for idx, row in df.iterrows():
        q = str(row.get(q_col, "")).strip()
        if not q:
            continue
        print(f"[{idx+1}/{total}] Q: {q[:80]}...")
        snippets = rag.query(q)
        context = build_context(snippets)
        ans = llm.generate(TEMPLATE.format(question=q, context=context), max_tokens=max_tokens)
        df.at[idx, a_col] = ans
    df.to_excel(output_xlsx, index=False)
    print(f"[OK] Planilha gerada em: {output_xlsx}")


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).with_name("settings.env"), override=False)
    load_dotenv(override=False)

    parser = argparse.ArgumentParser(description="RAG local para responder planilhas de segurança.")
    sub = parser.add_subparsers(dest="cmd")
    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("--dir", default=os.getenv("KNOWLEDGE_DIR", "./knowledge"))

    p_ans = sub.add_parser("answer")
    p_ans.add_argument("--input", required=True)
    p_ans.add_argument("--sheet", default="Perguntas")
    p_ans.add_argument("--qcol", default="Question")
    p_ans.add_argument("--acol", default="Answer")
    p_ans.add_argument("--output", required=True)

    args = parser.parse_args()

    MODEL_NAME   = os.getenv("MODEL_NAME", "llama3:8b")
    EMBED_MODEL  = os.getenv("EMBED_MODEL", "nomic-embed-text")
    KNOWLEDGE_DIR= os.getenv("KNOWLEDGE_DIR", "./knowledge")
    VECTOR_DB_DIR= os.getenv("VECTOR_DB_DIR", "./chroma_store")
    TOP_K        = int(os.getenv("TOP_K", "6"))
    MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "512"))
    OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")

    embedder = LocalHFEmbedder()
    rag = LocalRAG(VECTOR_DB_DIR, embedder, top_k=TOP_K)
    llm = OllamaLLM(OLLAMA_URL, MODEL_NAME)

    if args.cmd == "ingest":
        folder = Path(args.dir)
        if not folder.exists():
            print(f"Pasta não encontrada: {folder}")
            sys.exit(1)
        rag.ingest_folder(folder)

    elif args.cmd == "answer":
        # Warm-up para evitar timeout na 1ª requisição
        llm.warmup()
        process_excel(Path(args.input), Path(args.output), args.sheet, args.qcol, args.acol, rag, llm, MAX_TOKENS)

    else:
        parser.print_help()