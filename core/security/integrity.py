import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class LogIntegrityBlock(BaseModel):
    block_index: int
    prev_hash: str
    record_count: int
    merkle_root: str
    timestamp: str
    block_hash: str
    records: List[str] = Field(default_factory=list)

class LogIntegrityEngine:
    GENESIS_PREV_HASH = "0" * 64

    def __init__(self):
        self.chain: List[LogIntegrityBlock] = []

    def calculate_merkle_root(self, records: List[str]) -> str:
        if not records:
            return hashlib.sha256(b"empty_block").hexdigest()
        hashes = [hashlib.sha256(r.encode("utf-8")).hexdigest() for r in records]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            hashes = next_level
        return hashes[0]

    def calculate_block_hash(self, block_index: int, prev_hash: str, merkle_root: str, record_count: int, timestamp: str) -> str:
        payload = f"{block_index}|{prev_hash}|{merkle_root}|{record_count}|{timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal_block(self, records: List[str]) -> LogIntegrityBlock:
        block_idx = len(self.chain)
        prev_h = self.chain[-1].block_hash if self.chain else self.GENESIS_PREV_HASH
        ts = datetime.now(timezone.utc).isoformat()
        root = self.calculate_merkle_root(records)
        b_hash = self.calculate_block_hash(block_idx, prev_h, root, len(records), ts)

        block = LogIntegrityBlock(
            block_index=block_idx,
            prev_hash=prev_h,
            record_count=len(records),
            merkle_root=root,
            timestamp=ts,
            block_hash=b_hash,
            records=records
        )
        self.chain.append(block)
        return block

    def verify_chain(self) -> Dict[str, Any]:
        if not self.chain:
            return {"is_valid": True, "total_blocks": 0, "message": "Chain is empty"}

        for idx, block in enumerate(self.chain):
            expected_prev = self.chain[idx - 1].block_hash if idx > 0 else self.GENESIS_PREV_HASH
            if block.prev_hash != expected_prev:
                return {
                    "is_valid": False,
                    "tampered_block_index": idx,
                    "error": "Previous hash mismatch (broken chain link)"
                }

            expected_merkle = self.calculate_merkle_root(block.records)
            if block.merkle_root != expected_merkle:
                return {
                    "is_valid": False,
                    "tampered_block_index": idx,
                    "error": "Merkle root mismatch (record modification detected)"
                }

            expected_hash = self.calculate_block_hash(
                block.block_index,
                block.prev_hash,
                block.merkle_root,
                block.record_count,
                block.timestamp
            )
            if block.block_hash != expected_hash:
                return {
                    "is_valid": False,
                    "tampered_block_index": idx,
                    "error": "Block hash mismatch (header tampering detected)"
                }

        return {
            "is_valid": True,
            "total_blocks": len(self.chain),
            "latest_block_hash": self.chain[-1].block_hash,
            "message": "All blocks cryptographically verified with 100% integrity."
        }

    def get_chain_summary(self) -> Dict[str, Any]:
        return {
            "total_blocks": len(self.chain),
            "total_records": sum(b.record_count for b in self.chain),
            "latest_block_index": self.chain[-1].block_index if self.chain else None,
            "latest_hash": self.chain[-1].block_hash if self.chain else None
        }

integrity_engine = LogIntegrityEngine()
