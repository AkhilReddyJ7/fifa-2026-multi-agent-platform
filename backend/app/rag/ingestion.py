"""Ingest historical World Cup documents into ChromaDB."""

from __future__ import annotations

import structlog

from app.core.config import get_settings
from app.rag.chroma_client import upsert_documents

log = structlog.get_logger()
settings = get_settings()

# Sample historical narratives — in production these come from a data pipeline
WC_HISTORY_DOCS = [
    {
        "id": "wc_2022_final",
        "text": (
            "2022 FIFA World Cup Final — Argentina vs France. Played at Lusail Stadium, Qatar. "
            "Argentina won 4-2 on penalties after a 3-3 draw (AET). Kylian Mbappé scored a hat-trick. "
            "Lionel Messi scored twice and won the Golden Ball award."
        ),
        "meta": {"year": 2022, "stage": "final", "teams": "ARG,FRA"},
    },
    {
        "id": "wc_2018_final",
        "text": (
            "2018 FIFA World Cup Final — France vs Croatia. Played at Luzhniki Stadium, Moscow. "
            "France won 4-2. Goals from Mandžukić (OG), Griezmann (pen), Pogba, Mbappé. "
            "France became world champions for the second time."
        ),
        "meta": {"year": 2018, "stage": "final", "teams": "FRA,CRO"},
    },
    {
        "id": "wc_2014_final",
        "text": (
            "2014 FIFA World Cup Final — Germany vs Argentina. Played at Estádio do Maracanã, Rio de Janeiro. "
            "Germany won 1-0 with a Mario Götze goal in extra time. Germany became the first European team "
            "to win the World Cup on South American soil."
        ),
        "meta": {"year": 2014, "stage": "final", "teams": "GER,ARG"},
    },
    {
        "id": "wc_2010_final",
        "text": (
            "2010 FIFA World Cup Final — Spain vs Netherlands. Played at Soccer City, Johannesburg. "
            "Spain won 1-0 with an Andrés Iniesta goal in extra time. Spain became world champions "
            "for the first time in their history."
        ),
        "meta": {"year": 2010, "stage": "final", "teams": "ESP,NED"},
    },
    {
        "id": "wc_2006_final",
        "text": (
            "2006 FIFA World Cup Final — Italy vs France. Played at Olympiastadion, Berlin. "
            "Italy won 5-3 on penalties after a 1-1 draw (AET). Zinédine Zidane was sent off "
            "for headbutting Marco Materazzi. Fabio Cannavaro won the Golden Ball."
        ),
        "meta": {"year": 2006, "stage": "final", "teams": "ITA,FRA"},
    },
]


def ingest_wc_history() -> None:
    ids = [d["id"] for d in WC_HISTORY_DOCS]
    texts = [d["text"] for d in WC_HISTORY_DOCS]
    metas = [d["meta"] for d in WC_HISTORY_DOCS]
    upsert_documents(settings.chroma_collection_wc_history, ids=ids, documents=texts, metadatas=metas)
    log.info("rag.ingestion.complete", collection=settings.chroma_collection_wc_history, docs=len(ids))
