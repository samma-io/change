import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';

const NATS_ENABLED = process.env.NATS_ENABLED;
const OUT_DIR = process.env.OUT_DIR || '/out';
const NATS_URL = process.env.NATS_URL || 'nats://localhost:4222';
const BUCKET = 'web-change-scanner';

function sanitizeDomain(domain) {
  return domain.replace(/\./g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
}

function filePath(domain) {
  return path.join(OUT_DIR, 'web-change-scanner.' + domain + '.baseline.json');
}

async function fsLoad(domain) {
  const fp = filePath(domain);
  try {
    const raw = await readFile(fp, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    if (err.code === 'ENOENT') return null;
    process.stderr.write(`[storage] warning: failed to read ${fp}: ${err.message}\n`);
    return null;
  }
}

async function fsSave(domain, snapshot) {
  await mkdir(OUT_DIR, { recursive: true });
  const fp = filePath(domain);
  await writeFile(fp, JSON.stringify(snapshot, null, 2));
}

async function natsLoad(domain) {
  const { connect, StringCodec } = await import('nats');
  const sc = StringCodec();
  const key = sanitizeDomain(domain);
  const nc = await connect({ servers: NATS_URL });
  try {
    const js = nc.jetstream();
    const kv = await js.views.kv(BUCKET, { history: 1 });
    const entry = await kv.get(key);
    const value = entry ? sc.decode(entry.value) : null;
    return value ? JSON.parse(value) : null;
  } finally {
    await nc.drain();
  }
}

async function natsSave(domain, snapshot) {
  const { connect, StringCodec } = await import('nats');
  const sc = StringCodec();
  const key = sanitizeDomain(domain);
  const nc = await connect({ servers: NATS_URL });
  try {
    const js = nc.jetstream();
    const kv = await js.views.kv(BUCKET, { history: 1 });
    await kv.put(key, sc.encode(JSON.stringify(snapshot)));
  } finally {
    await nc.drain();
  }
}

export async function load(domain) {
  if (NATS_ENABLED !== 'False') {
    try {
      return await natsLoad(domain);
    } catch (err) {
      process.stderr.write(`[storage] warning: NATS load failed, falling back to filesystem: ${err.message}\n`);
      return await fsLoad(domain);
    }
  }
  return await fsLoad(domain);
}

export async function save(domain, snapshot) {
  if (NATS_ENABLED !== 'False') {
    try {
      return await natsSave(domain, snapshot);
    } catch (err) {
      process.stderr.write(`[storage] warning: NATS save failed, falling back to filesystem: ${err.message}\n`);
      return await fsSave(domain, snapshot);
    }
  }
  return await fsSave(domain, snapshot);
}
