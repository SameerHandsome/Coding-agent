# app/rag/indexer.py
from app.rag.hybrid_search import hybrid_searcher
from app.tools.token_counter import count_tokens
from typing import List, Dict


class CodeIndexer:
    def _chunk(self, text: str, size: int = 500) -> List[str]:
        lines, chunks, cur, cur_tok = text.split("\n"), [], [], 0
        for line in lines:
            lt = count_tokens(line)
            if cur_tok + lt > size and cur:
                chunks.append("\n".join(cur))
                cur = [line]
                cur_tok = lt
            else:
                cur.append(line)
                cur_tok += lt
        if cur:
            chunks.append("\n".join(cur))
        return chunks

    async def index_code_files(
        self, files: List[Dict], stack: str, session_id: str
    ) -> None:
        chunks = []
        for f in files:
            for i, chunk in enumerate(self._chunk(f["content"])):
                chunks.append(
                    {
                        "text": chunk,
                        "payload": {
                            "type": "code_pattern",
                            "stack": stack,
                            "file_path": f["path"],
                            "chunk_idx": i,
                            "session_id": session_id,
                        },
                    }
                )
        if chunks:
            await hybrid_searcher.upsert(chunks)

    async def index_error_fix_pair(self, error: str, fix: str, stack: str) -> None:
        await hybrid_searcher.upsert(
            [
                {
                    "text": f"ERROR:\n{error}\n\nFIX:\n{fix}",
                    "payload": {
                        "type": "error_fix_pair",
                        "error": error,
                        "fix": fix,
                        "stack": stack,
                    },
                }
            ]
        )


code_indexer = CodeIndexer()
