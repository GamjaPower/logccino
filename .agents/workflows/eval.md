# Workflow: /eval
# 트리아지 및 DLP 에이전트의 정밀도/재현율 평가 및 혼동 행렬, 토큰 비용을 측정합니다.

1. 테스트 데이터셋 레이블 로드: `testdata/labels.jsonl`
2. 평가 하네스 실행: `go run ./cmd/eval --limit 50`
3. 프롬프트 간 상충 지침 정적 검사: `go run ./cmd/eval lint-prompts`
4. 결과 집계: 정확도(Accuracy), 혼동 행렬(Confusion Matrix), 불일치 티켓 목록, 총/평균 토큰 및 소요 시간 출력
