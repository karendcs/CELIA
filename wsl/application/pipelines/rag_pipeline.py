"""
Pipeline RAG para processamento de planilhas Excel.
Encapsula o fluxo completo: ler xlsx → responder cada linha → salvar xlsx.
Usa AnswerService para cada pergunta individualmente (testável e extensível).
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator

import pandas as pd

from config import Settings
from core.exceptions import AnswerError
from core.logging import get_logger
from application.services.answer_service import AnswerService

logger = get_logger("pipelines.rag")


class ExcelRAGPipeline:
    """
    Pipeline Pattern: processa um arquivo Excel linha a linha,
    gerando respostas via RAG e salvando o resultado.

    Emite linhas de log via `run()` como Generator para suportar
    streaming (SSE/HTTP Streaming) na camada de interface.
    """

    def __init__(self, answer_service: AnswerService, settings: Settings) -> None:
        self._svc = answer_service
        self._settings = settings

    def run(
        self,
        input_path: Path,
        output_path: Path,
        sheet: str,
        question_col: str,
        answer_col: str,
    ) -> Generator[str, None, None]:
        """
        Processa o Excel e gera linhas de log.
        Uso: for line in pipeline.run(...): print(line)
        """
        try:
            df = pd.read_excel(input_path, sheet_name=sheet)
        except Exception as exc:
            yield f"[ERRO] Falha ao abrir planilha: {exc}\n"
            return

        if answer_col not in df.columns:
            df[answer_col] = ""
        df[answer_col] = df[answer_col].astype(object)

        total = len(df)
        yield f"[INFO] Planilha carregada: {total} linhas | aba='{sheet}'\n"

        errors = 0
        for idx, row in df.iterrows():
            question = str(row.get(question_col, "")).strip()
            if not question:
                continue

            row_num = int(idx) + 1  # type: ignore[arg-type]
            yield f"[{row_num}/{total}] {question[:80]}...\n"

            try:
                result = self._svc.answer(question)
                df.at[idx, answer_col] = result.answer
                yield f"  → {result.answer[:100]}...\n" if len(result.answer) > 100 else f"  → {result.answer}\n"
            except AnswerError as exc:
                errors += 1
                df.at[idx, answer_col] = "Erro ao processar."
                yield f"  [WARN] {exc}\n"

        try:
            df.to_excel(output_path, index=False)
            yield f"\n[OK] Baixar planilha: /downloads/{output_path.name}\n"
        except Exception as exc:
            yield f"\n[ERRO] Falha ao salvar planilha: {exc}\n"

        if errors:
            yield f"[INFO] Concluído com {errors} erro(s) em {total} perguntas.\n"
        else:
            yield f"[INFO] Concluído sem erros ({total} perguntas processadas).\n"
