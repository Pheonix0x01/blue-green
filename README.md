# blue/green deployment

two identical services running behind nginx. one is active, other is backup. if active dies nginx automatically routes to backup. zero downtime.

ports:
- nginx: `localhost:8080`
- blue direct: `localhost:8081`
- green direct: `localhost:8082`

## setup

you need docker and docker compose. ports 8080, 8081, 8082 need to be free.

```bash
git clone https://github.com/Pheonix0x01/blue-green.git
cd blue-green
cp .env.example .env
chmod +x entrypoint.sh
docker compose up -d
```

test it works:
```bash
curl -i http://localhost:8080/version
```

should see `X-App-Pool: blue` in the headers.

## testing failover

break blue and watch nginx route to green automatically:

```bash
curl -i http://localhost:8080/version

curl -X POST "http://localhost:8081/chaos/start?mode=error"

for i in {1..10}; do 
    curl -s http://localhost:8080/version | grep X-App-Pool
    sleep 0.5
done

curl -X POST http://localhost:8081/chaos/stop
sleep 6
curl -i http://localhost:8080/version
```

all requests succeed even when blue is broken. thats the point.

chaos modes:
```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
curl -X POST "http://localhost:8081/chaos/start?mode=timeout"
curl http://localhost:8081/chaos/status
curl -X POST http://localhost:8081/chaos/stop
```

## manual switching

edit `.env` and change `ACTIVE_POOL=blue` to `ACTIVE_POOL=green` then:

```bash
docker compose restart nginx
curl -i http://localhost:8080/version
```

## logs and debugging

```bash
docker compose logs -f
docker compose logs -f nginx
docker compose exec nginx cat /etc/nginx/conf.d/default.conf
docker compose exec nginx nginx -t
```

health checks:
```bash
curl http://localhost:8081/healthz
curl http://localhost:8082/healthz
docker compose ps
```

## how it works

nginx watches both pools with health checks. if blue fails twice in 5 seconds nginx marks it down and sends traffic to green. requests that hit a dead server get automatically retried on the backup server so clients never see errors. after blue recovers nginx tries it again and switches back.

timeouts are aggressive: 3s connection, 3s read, up to 3 retries within 9s total.

## cleanup

```bash
docker compose down
docker compose down -v
```

## observability

stage 3 adds slack alerts for failovers and high error rates. nginx logs pool and release info. python watcher parses logs and sends alerts.

## slack setup

you need a slack webhook. go to https://api.slack.com/apps and create an app. add incoming webhooks feature and create one for your channel. put the webhook url in `.env`.

```bash
cp .env.example .env
nano .env
docker compose up -d
docker logs -f log_watcher
```

## test failover alert

```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"

for i in {1..20}; do curl http://localhost:8080/version; sleep 0.5; done

curl -X POST http://localhost:8081/chaos/stop
```

check slack for the failover alert.

## test error rate alert

```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
for i in {1..250}; do curl http://localhost:8080/version; done
curl -X POST http://localhost:8081/chaos/stop
```

check slack for the error rate alert.

## checking logs

nginx logs:
```bash
docker exec nginx_proxy tail -f /var/log/nginx/access.log
```

watcher output:
```bash
docker logs -f log_watcher
```

should see pool detection, failover messages, error rate calculations, and slack confirmations.

## troubleshooting

watcher not starting:
```bash
docker logs log_watcher
```

slack not working:
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  $SLACK_WEBHOOK_URL
```

no failover detected:
```bash
curl http://localhost:8081/chaos/status
docker logs nginx_proxy
docker exec nginx_proxy cat /etc/nginx/conf.d/default.conf
```