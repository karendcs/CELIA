"""Comandos CLI: ingest e answer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import get_settings
from core.logging import setup_logging, get_logger
from application.container import build_ingest_service, build_excel_pipeline

logger = get_logger("cli")


def cmd_ingest(args: argparse.Namespace) -> int:
    folder = Path(args.dir)
    if not folder.exists():
        logger.error("Pasta não encontrada: %s", folder)
        return 1
    svc = build_ingest_service()
    count = svc.ingest_folder(folder)
    logger.info("Ingestão concluída: %d chunks.", count)
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    s = get_settings()
    pipeline = build_excel_pipeline(s)

    # Warm-up do LLM antes do processamento
    from application.container import build_answer_service
    svc = build_answer_service(s)
    svc._llm.warmup()  # type: ignore[attr-defined]

    for line in pipeline.run(
        input_path=Path(args.input),
        output_path=Path(args.output),
        sheet=args.sheet,
        question_col=args.qcol,
        answer_col=args.acol,
    ):
        print(line, end="", flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CelIA — CLI RAG para planilhas.")
    sub = parser.add_subparsers(dest="cmd")

    p_ing = sub.add_parser("ingest", help="Ingerir documentos na base de conhecimento.")
    p_ing.add_argument("--dir", default=str(get_settings().knowledge_dir))

    p_ans = sub.add_parser("answer", help="Responder planilha Excel via RAG.")
    p_ans.add_argument("--input", required=True, help="Caminho do .xlsx de entrada.")
    p_ans.add_argument("--output", required=True, help="Caminho do .xlsx de saída.")
    p_ans.add_argument("--sheet", default="Perguntas", help="Nome da aba.")
    p_ans.add_argument("--qcol", default="Pergunta", help="Coluna de perguntas.")
    p_ans.add_argument("--acol", default="Resposta", help="Coluna de respostas.")

    return parser


def main() -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "ingest":
        return cmd_ingest(args)
    if args.cmd == "answer":
        return cmd_answer(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
