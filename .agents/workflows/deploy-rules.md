# Workflow: /deploy-rules
# 탐지 규칙의 검증, 컴파일, 배포 및 사후 검증, 자동 롤백 파이프라인을 실행합니다.

1. 규칙 검증: `go run ./cmd/dacctl validate rules/detections/`
2. 컴파일 및 배포 계획: `go run ./cmd/dacctl plan`
3. 자동 백업 및 배포 실행: `go run ./cmd/dacctl deploy`
4. 사후 검증 및 드리프트 점검: `go run ./cmd/dacctl drift`
