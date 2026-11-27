# Build stage
FROM golang:alpine AS builder

WORKDIR /app

ENV GOTOOLCHAIN=auto

RUN apk add --no-cache git ca-certificates

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /bin/server ./cmd/server
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /bin/dacctl ./cmd/dacctl

# Runtime stage
FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata curl git && \
    mkdir -p /app/data /app/rules /app/build

COPY --from=builder /bin/server /app/server
COPY --from=builder /bin/dacctl /app/dacctl
COPY --from=builder /app/prompts /app/prompts

EXPOSE 5090

ENTRYPOINT ["/app/server"]
