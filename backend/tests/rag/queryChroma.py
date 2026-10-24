import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app"))

from ai.rag.handbook import handbook_retriever


async def main():
    query = " ".join(sys.argv[1:]) or "welfare"
    for doc in await handbook_retriever.search(query, k=5):
        print(f"--- p.{doc.metadata['page']} {doc.metadata['section']}\n{doc.page_content[:300]}\n")


asyncio.run(main())
