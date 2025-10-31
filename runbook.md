# runbook

## when failover happens

nginx detected blue failed and switched to green. clients didnt notice because requests succeeded via automatic retry.

what to do:

```bash
docker logs app_blue
curl http://localhost:8081/healthz
```

if blue is broken check the logs for errors, look at cpu and memory usage. restart if needed:

```bash
docker restart app_blue
```

blue will auto recover after 5 seconds if it comes back healthy. youll see traffic switch back.

escalate if blue doesnt recover in 5 minutes, green also starts failing, or it keeps flapping between pools.

## when error rate is high

more than 2% of requests are returning 5xx errors. something is wrong with the app.

check which pool is active:

```bash
curl -i http://localhost:8080/version | grep X-App-Pool
docker logs app_blue --tail 100
docker stats app_blue app_green
```

if errors continue switch pools manually:

```bash
docker restart nginx
```

or restart the broken container:

```bash
docker restart app_blue
```

check if database or external apis are down.

escalate if error rate goes over 10%, both pools are failing, or switching doesnt help.

## when recovery happens

blue came back and traffic switched from green back to blue. system is back to normal.

verify blue is stable:

```bash
curl http://localhost:8081/version
docker logs app_blue --tail 50
```

if blue fails again within 5 minutes find the root cause. might be resource issues or memory leaks.

## maintenance mode

stop alerts during planned work:

```bash
docker stop log_watcher
docker start log_watcher
```

or increase cooldown:

```bash
ALERT_COOLDOWN_SEC=3600

docker restart log_watcher
```

## troubleshooting

watcher not sending alerts:

```bash
docker compose exec watcher tail -n 5 /var/log/nginx/access.log
```

common issues: bad slack webhook url, log file permissions, network problems.

test webhook:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"test alert"}' \
  $SLACK_WEBHOOK_URL
```

too many false alerts:

increase `fail_timeout` or `max_fails` in nginx config. increase `ERROR_RATE_THRESHOLD` in .env. increase `ALERT_COOLDOWN_SEC` to reduce frequency.

## best practices

set up dedicated slack channel for alerts. have someone on call. test failover monthly with chaos mode. keep nginx logs for incident analysis.