#!/usr/bin/env python3
"""
Logccino Big Data Sample Seeder
전사 서비스 24시간 안정성 통계표(payment-service, auth-service, notification-service)에
정확히 부합하는 대규모 로그 데이터 시뮬레이션 샘플을 OpenSearch에 주입합니다.
"""

import os
import sys
import random
from datetime import datetime, timedelta, timezone
from opensearchpy import OpenSearch, helpers

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
INDEX_PREFIX = os.getenv("OPENSEARCH_INDEX_PREFIX", "logccino-logs")

# 서비스별 시뮬레이션 데이터 정의
SERVICES_SPEC = {
    "payment-service": {
        "total_count": 14200,   # 14.2M 시뮬레이션 축소 비율
        "error_count": 43,      # 에러율 0.30% (주의 ⚠️)
        "hosts": ["pay-prod-01", "pay-prod-02", "pay-prod-03"],
        "info_messages": [
            "Payment authorization succeeded. Amount: 49000 KRW, card: VISA-**12",
            "Checkout session created for order ord_{id}",
            "Refund processed successfully for transaction tx_{id}",
            "Payment webhook dispatched to merchant portal",
            "Card tokenization completed successfully"
        ],
        "error_messages": [
            "PaymentGatewayTimeout: Stripe gateway did not respond within 5000ms [order=ord_{id}]",
            "SocketTimeoutException: Read timed out connecting to PG proxy at 10.0.4.12:8443",
            "CardDeclinedException: Insufficient funds or bank rejection code 51"
        ]
    },
    "auth-service": {
        "total_count": 8900,    # 8.9M 시뮬레이션 축소 비율
        "error_count": 1,       # 에러율 0.01% (정상 ✅)
        "hosts": ["auth-prod-01", "auth-prod-02"],
        "info_messages": [
            "User login successful for account: user_{id}@company.com",
            "OAuth2 JWT token issued. Expires in 3600s",
            "Multi-factor authentication (MFA) verified via TOTP",
            "User session refreshed successfully",
            "Password validation passed for user_{id}"
        ],
        "error_messages": [
            "DatabaseConnectionTimeoutException: Failed to acquire DB pool connection after 3000ms"
        ]
    },
    "notification-service": {
        "total_count": 3100,    # 3.1M 시뮬레이션 축소 비율
        "error_count": 89,      # 에러율 2.87% (경고 🔴)
        "hosts": ["noti-worker-01", "noti-worker-02"],
        "info_messages": [
            "Push notification delivered to device token: fcm_tok_{id}",
            "Transactional email sent via AWS SES to user_{id}@domain.com",
            "Kakao Alimtalk message dispatched successfully",
            "SMS notification queued for delivery"
        ],
        "error_messages": [
            "FCMDeliveryFailureException: APNs/FCM push token invalid or unregistered [device={id}]",
            "SMSGatewayQuotaExceeded: Daily SMS quota exceeded (429 Too Many Requests) on provider KT",
            "NotificationDeliveryTimeout: Webhook endpoint timed out after 3000ms"
        ]
    }
}

def generate_logs(today_str: str):
    now = datetime.now(timezone.utc)
    docs = []

    for svc_name, spec in SERVICES_SPEC.items():
        total = spec["total_count"]
        errors = spec["error_count"]
        infos = total - errors

        print(f"Generating {total} logs for {svc_name} (Errors: {errors}, Error Rate: {errors/total*100:.2f}%)...")

        # 1. INFO logs
        for _ in range(infos):
            time_offset = random.randint(0, 86400) # 최근 24시간 분산
            log_time = (now - timedelta(seconds=time_offset)).isoformat()
            rid = random.randint(10000, 99999)
            msg = random.choice(spec["info_messages"]).replace("{id}", str(rid))
            docs.append({
                "_index": f"{INDEX_PREFIX}-{today_str}",
                "_source": {
                    "@timestamp": log_time,
                    "service": svc_name,
                    "level": "INFO",
                    "host": random.choice(spec["hosts"]),
                    "message": msg,
                    "trace_id": f"tr-{random.randint(100000, 999999)}",
                    "sourcetype": "json"
                }
            })

        # 2. ERROR logs
        for _ in range(errors):
            time_offset = random.randint(0, 86400)
            log_time = (now - timedelta(seconds=time_offset)).isoformat()
            rid = random.randint(10000, 99999)
            msg = random.choice(spec["error_messages"]).replace("{id}", str(rid))
            docs.append({
                "_index": f"{INDEX_PREFIX}-{today_str}",
                "_source": {
                    "@timestamp": log_time,
                    "service": svc_name,
                    "level": "ERROR",
                    "host": random.choice(spec["hosts"]),
                    "message": msg,
                    "trace_id": f"tr-{random.randint(100000, 999999)}",
                    "sourcetype": "json"
                }
            })

    random.shuffle(docs)
    return docs

def main():
    print(f"Connecting to OpenSearch at {OPENSEARCH_HOST}...")
    client = OpenSearch(hosts=[OPENSEARCH_HOST], ssl_show_warn=False)

    if not client.ping():
        print(f"❌ Cannot connect to OpenSearch at {OPENSEARCH_HOST}.")
        print("💡 OpenSearch 컨테이너가 실행 중인지 확인해 주세요 (`docker compose up -d` 또는 `sudo docker compose up -d`).")
        sys.exit(1)

    today_str = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    docs = generate_logs(today_str)

    print(f"Bulk indexing {len(docs)} documents into '{INDEX_PREFIX}-{today_str}'...")
    success, failed = helpers.bulk(client, docs, chunk_size=2000, request_timeout=60)
    print(f"✅ Successfully indexed {success} logs into OpenSearch! (Failed: {len(failed) if isinstance(failed, list) else failed})")
    print("\n🎉 전사 서비스 24시간 안정성 통계표 데이터 주입이 완료되었습니다!")

if __name__ == "__main__":
    main()
