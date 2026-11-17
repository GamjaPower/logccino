import re
from typing import Dict, Any, List

class PIIMaskingEngine:
    RRN_PATTERN = re.compile(r'\b(\d{6})[- ]?([1-4]\d{6})\b')
    CARD_PATTERN = re.compile(r'\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b')
    PHONE_PATTERN = re.compile(r'\b(01[016789])[- ]?(\d{3,4})[- ]?(\d{4})\b')
    EMAIL_PATTERN = re.compile(r'\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b')
    ACCOUNT_PATTERN = re.compile(r'\b(\d{3,6})[- ]?(\d{2,6})[- ]?(\d{3,8})\b')

    @classmethod
    def mask_text(cls, text: str) -> str:
        if not text or not isinstance(text, str):
            return text
        text = cls.RRN_PATTERN.sub(r'\1-\2', text)
        text = cls.RRN_PATTERN.sub(lambda m: f"{m.group(1)}-{m.group(2)[0]}******", text)
        text = cls.CARD_PATTERN.sub(r'\1-****-****-\4', text)
        text = cls.PHONE_PATTERN.sub(r'\1-****-\3', text)
        text = cls.EMAIL_PATTERN.sub(r'\1***@\2', text)
        return text

    @classmethod
    def mask_record(cls, record: Any) -> Any:
        if isinstance(record, dict):
            return {k: cls.mask_record(v) for k, v in record.items()}
        elif isinstance(record, list):
            return [cls.mask_record(v) for v in record]
        elif isinstance(record, str):
            return cls.mask_text(record)
        return record

    @classmethod
    def detect_pii(cls, text: str) -> List[Dict[str, Any]]:
        findings = []
        if not text or not isinstance(text, str):
            return findings

        rrn_matches = cls.RRN_PATTERN.findall(text)
        if rrn_matches:
            findings.append({"type": "RRN", "count": len(rrn_matches), "description": "주민등록번호 패턴 탐지"})

        card_matches = cls.CARD_PATTERN.findall(text)
        if card_matches:
            findings.append({"type": "CARD", "count": len(card_matches), "description": "신용카드 번호 패턴 탐지"})

        phone_matches = cls.PHONE_PATTERN.findall(text)
        if phone_matches:
            findings.append({"type": "PHONE", "count": len(phone_matches), "description": "휴대전화 번호 패턴 탐지"})

        email_matches = cls.EMAIL_PATTERN.findall(text)
        if email_matches:
            findings.append({"type": "EMAIL", "count": len(email_matches), "description": "이메일 주소 패턴 탐지"})

        return findings

pii_masker = PIIMaskingEngine()
