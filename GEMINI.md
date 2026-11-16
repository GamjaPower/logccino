# Logccino Project Guidelines & Antigravity Rules

## 🚀 자동 Git Commit & Push 규칙 (Mandatory Rule)

에이전트는 작업 수행 중 **큰 변화나 로직의 변화(주요 아키텍처 전환, 새 모듈/기능 추가, 핵심 비즈니스 로직 수정, 대규모 리팩토링 등)**가 있을 때, 사용자의 별도 요청이 없더라도 작업 단위를 완료하는 시점에 **자동으로 변경사항을 커밋하고 원격 저장소에 푸시(commit & push)**해야 합니다.

### 커밋 & 푸시 실행 기준
1. **아키텍처 및 설정의 중대한 전환**: 모듈 구조 개편, MCP 도입, 주요 인터페이스 변경 등
2. **새로운 기능/도구 추가 및 로직 구현**: 핵심 API, MCP 도구, 파이프라인 추가/수정 완료 시
3. **검증 필수**: 커밋 전 코드 문법 검사(`python -m py_compile`) 또는 관련 테스트를 통과한 후 커밋 수행
4. **커밋 메시지 형식**: Conventional Commits 규격을 준수하여 명확한 한국어/영어 요약 작성
   - `feat: ...` : 새로운 기능 및 도구 추가
   - `refactor: ...` : 아키텍처 및 로직 구조 변경
   - `fix: ...` : 버그 및 오류 수정
   - `docs: ...` : 문서 및 가이드 추가/수정
5. **푸시 자동화**: 커밋 직후 현재 작업 브랜치(`git push origin <branch>`)로 푸시까지 자동으로 완료하고 결과를 사용자에게 보고

---

## ☕ Logccino 프로젝트 핵심 원칙
- **AI Agent-Native**: 주 인터페이스는 Model Context Protocol (MCP) 기반으로 Claude, Antigravity 등의 외부 에이전트와 통신합니다.
- **Kibana/대시보드 종속 제거**: 5601 포트를 사용하는 Kibana는 사용하지 않으며, 자체 관리 UI(`frontend/`)와 MCP 도구 위주로 동작합니다.
- **클린 코드 & 타입 힌트**: Python 3.10+ 기반 타입 힌팅 및 Pydantic 데이터 검증을 준수합니다.
