---
trigger: always_on
description: 큰 변화나 로직 변경 완료 시 자동 git commit & push 수행 규칙
---

# Auto Git Commit & Push Rule

- 작업 중 **주요 아키텍처 전환, 새 모듈/기능 추가, 핵심 비즈니스 로직 수정, 대규모 리팩토링 등 큰 변화**가 있을 때는 작업을 마무리할 때 사용자의 별도 요청이 없어도 **반드시 자동으로 git commit 및 git push를 수행**한다.
- 커밋 메시지는 Conventional Commits 규격을 따르고, 의미 있는 요약 메시지를 작성한다.
- 커밋 전 문법/컴파일 검증을 거친 후 푸시를 완료하고 사용자에게 커밋 해시와 결과를 보고한다.
