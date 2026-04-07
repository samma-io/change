import os
import re
import sys
import json
import asyncio

NATS_ENABLED = os.getenv('NATS_ENABLED', 'False')
OUT_DIR = os.getenv('OUT_DIR', '/out')
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')
BUCKET = 'network-change-scanner'


def sanitize_key(key: str) -> str:
    key = re.sub(r'[.:]', '_', key)
    return re.sub(r'[^a-zA-Z0-9_-]', '', key)


def _file_path(target_key: str) -> str:
    return os.path.join(OUT_DIR, f'network-change-scanner.{target_key}.baseline.json')


# --- Filesystem mode ---

def _fs_load(target_key: str) -> dict | None:
    fp = _file_path(target_key)
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            return json.loads(fh.read())
    except FileNotFoundError:
        return None
    except Exception as e:
        sys.stderr.write(f'[storage] warning: failed to read {fp}: {e}\n')
        return None


def _fs_save(target_key: str, snapshot: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    fp = _file_path(target_key)
    with open(fp, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(snapshot, indent=2))


# --- NATS KV mode ---

async def _nats_load(target_key: str) -> dict | None:
    import nats
    import nats.js.api

    key = sanitize_key(target_key)
    nc = await nats.connect(NATS_URL)
    try:
        js = nc.jetstream()
        try:
            kv = await js.key_value(BUCKET)
        except Exception:
            kv = await js.create_key_value(
                nats.js.api.KeyValueConfig(bucket=BUCKET, history=1)
            )
        try:
            entry = await kv.get(key)
            return json.loads(entry.value.decode())
        except Exception:
            return None
    finally:
        await nc.drain()


async def _nats_save(target_key: str, snapshot: dict) -> None:
    import nats
    import nats.js.api

    key = sanitize_key(target_key)
    nc = await nats.connect(NATS_URL)
    try:
        js = nc.jetstream()
        try:
            kv = await js.key_value(BUCKET)
        except Exception:
            kv = await js.create_key_value(
                nats.js.api.KeyValueConfig(bucket=BUCKET, history=1)
            )
        await kv.put(key, json.dumps(snapshot).encode())
    finally:
        await nc.drain()


# --- Public interface ---

def load(target_key: str) -> dict | None:
    if NATS_ENABLED != 'False':
        try:
            return asyncio.run(_nats_load(target_key))
        except Exception as e:
            sys.stderr.write(
                f'[storage] warning: NATS load failed, falling back to filesystem: {e}\n'
            )
            return _fs_load(target_key)
    return _fs_load(target_key)


def save(target_key: str, snapshot: dict) -> None:
    if NATS_ENABLED != 'False':
        try:
            asyncio.run(_nats_save(target_key, snapshot))
            return
        except Exception as e:
            sys.stderr.write(
                f'[storage] warning: NATS save failed, falling back to filesystem: {e}\n'
            )
            _fs_save(target_key, snapshot)
            return
    _fs_save(target_key, snapshot)
