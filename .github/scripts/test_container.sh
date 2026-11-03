#!/usr/bin/env bash
set -euo pipefail

image="$1"
expected_arch="$2"
data_dir="$(mktemp -d)"

# 不访问外网：无效时间应被记录到挂载目录，并以非零状态退出。
printf "E_COOKIE='event=111'\nLOG_ENABLED='true'\nE_SCHEDULE='12:30,06:30'\n" > "$data_dir/.env"
if docker run --rm --user "$(id -u):$(id -g)" -v "$data_dir:/data" "$image" > "$data_dir/output" 2>&1; then
  echo 'Container unexpectedly accepted an invalid schedule.' >&2
  exit 1
fi
grep -q 'E_SCHEDULE' "$data_dir/output"
grep -q 'E_SCHEDULE' "$data_dir/logs/ehentai.log"
if grep -q 'Traceback' "$data_dir/output"; then
  echo 'Container printed a traceback.' >&2
  exit 1
fi

# 验证容器架构，以及 Cookie 原子替换确实写回挂载目录。
docker run --rm --user "$(id -u):$(id -g)" -v "$data_dir:/data" \
  --entrypoint python "$image" -c \
  'import platform, sys; from ehentai.config import save_cookie; assert platform.machine() == sys.argv[1]; save_cookie("event=222")' \
  "$expected_arch"
grep -q 'event=222' "$data_dir/.env"
echo 'Container architecture, startup errors, logs and Cookie persistence verified.'
