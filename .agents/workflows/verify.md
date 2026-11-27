# Workflow: /verify
# 린트, 정적 분석, 단위 테스트 및 docker compose 서비스 헬스체크를 순차적으로 실행합니다.

1. 코드 포맷팅 검증: `gofmt -l .` (수정 대상이 있으면 실패)
2. Go Vet 검증: `go vet ./...`
3. Go 단위 테스트: `go test -v ./...`
4. Docker Compose 헬스체크: `docker compose ps`에서 `splunk`와 `siem-agent`가 healthy 상태인지 확인
