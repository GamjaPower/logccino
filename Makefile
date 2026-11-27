.PHONY: all preflight up down restart verify test build release clean

SHELL := /bin/bash
GO ?= go
VERSION ?= v1.0.0
RELEASE_TARGETS ?= linux/amd64 linux/arm64 darwin/arm64 windows/amd64
RELEASE_CMDS := server dacctl loggen loaddata eval

all: build

preflight:
	@echo "==> [Preflight] 1. 포트 점유 여부 점검 (5090, 8000, 8088, 8089, 9997)..."
	@OCCUPIED=0; \
	for port in 5090 8000 8088 8089 9997; do \
		if ss -ltn | grep -E "[:.]$$port\b" >/dev/null 2>&1; then \
			echo "ERROR: 포트 $$port 가 이미 호스트에서 점유 중입니다."; \
			ss -lptn "sport = :$$port" 2>/dev/null || true; \
			OCCUPIED=1; \
		fi \
	done; \
	if [ $$OCCUPIED -ne 0 ]; then \
		echo "ERROR: 포트 충돌로 인해 기동을 중단합니다. 점유 중인 프로세스를 확인하세요."; \
		exit 1; \
	fi; \
	echo "==> [Preflight] 포트 점유 없음 확인 완료."
	@echo "==> [Preflight] 2. SPLUNK_PASSWORD 강도 점검..."
	@if [ -f .env ]; then \
		PASS=$$(grep -E '^SPLUNK_PASSWORD=' .env | cut -d= -f2- | sed 's/^[ \t"'\''"]*//;s/[ \t"'\''"]*$$//'); \
		if [ -z "$$PASS" ] || [ $${#PASS} -lt 8 ]; then \
			echo "ERROR: SPLUNK_PASSWORD 가 비어 있거나 8자 미만입니다. 최소 8자 이상이어야 합니다."; \
			exit 1; \
		elif [ $${#PASS} -lt 12 ]; then \
			echo "WARN: SPLUNK_PASSWORD 가 12자 미만($${#PASS}자)입니다. 외부 공개 환경에서는 12자 이상을 권장합니다."; \
		else \
			echo "==> [Preflight] SPLUNK_PASSWORD 검증 완료 (길이: $${#PASS}자)."; \
		fi; \
	else \
		echo "WARN: .env 파일이 없습니다. 기본 템플릿 검사만 통과합니다."; \
	fi

up: preflight
	@echo "==> Docker Compose 서비스 기동..."
	docker compose up -d

down:
	@echo "==> Docker Compose 서비스 종료..."
	docker compose down

restart: down up

build:
	@echo "==> 바이너리 빌드..."
	@mkdir -p bin
	$(GO) build -v -o bin/server ./cmd/server
	$(GO) build -v -o bin/dacctl ./cmd/dacctl
	$(GO) build -v -o bin/loggen ./cmd/loggen
	$(GO) build -v -o bin/loaddata ./cmd/loaddata
	$(GO) build -v -o bin/eval ./cmd/eval

verify:
	@echo "==> 코드 포맷팅 검사 (gofmt)..."
	@UNFORMATTED=$$($(GO)fmt -l cmd internal); \
	if [ -n "$$UNFORMATTED" ]; then \
		echo "ERROR: 포맷팅이 맞지 않는 파일이 있습니다:"; \
		echo "$$UNFORMATTED"; \
		exit 1; \
	fi
	@echo "==> 정적 분석 (go vet)..."
	$(GO) vet ./cmd/... ./internal/...
	@echo "==> 단위 테스트 (go test)..."
	$(GO) test -v ./cmd/... ./internal/...
	@echo "==> Docker Compose 헬스체크..."
	@if docker compose ps 2>/dev/null | grep -q "splunk"; then \
		docker compose ps; \
	fi

test:
	$(GO) test -v ./cmd/... ./internal/...

release:
	@echo "==> [Release] $(VERSION) 아티팩트 빌드 시작..."
	@rm -rf dist && mkdir -p dist
	@for target in $(RELEASE_TARGETS); do \
		os=$${target%/*}; \
		arch=$${target#*/}; \
		ext=""; \
		if [ "$$os" = "windows" ]; then ext=".exe"; fi; \
		pkg="logccino_$(VERSION)_$${os}_$${arch}"; \
		stage="dist/$${pkg}"; \
		echo "--> 빌드: $${os}/$${arch} ($${pkg})"; \
		mkdir -p "$${stage}/bin"; \
		for c in $(RELEASE_CMDS); do \
			CGO_ENABLED=0 GOOS="$$os" GOARCH="$$arch" $(GO) build -trimpath -ldflags="-s -w" -o "$${stage}/bin/$${c}$${ext}" "./cmd/$${c}" || exit 1; \
		done; \
		cp -r prompts "$${stage}/prompts"; \
		tar --exclude='rules/build' --exclude='splunk/apps/*/local' --exclude='splunk/apps/*/metadata/local.meta' --exclude='*.tmp' -cf - rules splunk | tar -xf - -C "$${stage}"; \
		cp docker-compose.yml Dockerfile .env.example Makefile README.md CHANGELOG.md "$${stage}/"; \
		if [ "$$os" = "windows" ]; then \
			(cd dist && zip -rq "$${pkg}.zip" "$${pkg}") || exit 1; \
		else \
			tar -czf "dist/$${pkg}.tar.gz" -C dist "$${pkg}" || exit 1; \
		fi; \
		rm -rf "$${stage}"; \
	done
	@(cd dist && sha256sum logccino_$(VERSION)_*.tar.gz logccino_$(VERSION)_*.zip > checksums.txt)
	@echo "==> [Release] 체크섬 생성 완료:"
	@cat dist/checksums.txt

clean:
	rm -rf bin/ build/ dist/ data/*.db
