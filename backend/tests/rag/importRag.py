"""
Rebuild the employee handbook index (run from the backend folder):

    python tests/rag/importRag.py

The index is also built automatically when the server starts, run this after replacing the PDF.
"""
import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app"))

from ai.rag.handbook import handbook_retriever


async def main():
    count = await handbook_retriever.rebuild()
    print(f"Indexed {count} handbook chunks")
    for doc in await handbook_retriever.search("vacation", k=3):
        print(f"- p.{doc.metadata['page']} {doc.metadata['section']}")


asyncio.run(main())
