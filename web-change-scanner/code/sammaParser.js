import { writeFile, appendFile, mkdir } from 'fs/promises';
import path from 'node:path';

const WRITE_TO_FILE = process.env.WRITE_TO_FILE ?? 'False';
const PARSER = process.env.PARSER ?? 'web-change-scanner';
const OUT_DIR = process.env.OUT_DIR ?? '/out';
const SAMMA_IO_SCANNER = process.env.SAMMA_IO_SCANNER ?? 'web-change-scanner';
const SAMMA_IO_ID = process.env.SAMMA_IO_ID ?? '1234';
const SAMMA_IO_TAGS = (process.env.SAMMA_IO_TAGS ?? 'scanner').split(',');
const SAMMA_IO_JSON = (() => {
  try {
    return JSON.parse(process.env.SAMMA_IO_JSON ?? '{}');
  } catch {
    return {};
  }
})();
const NATS_ENABLED = process.env.NATS_ENABLED ?? 'False';
const NATS_URL = process.env.NATS_URL ?? 'nats://localhost:4222';
const NATS_SUBJECT = process.env.NATS_SUBJECT ?? 'samma-io.scan';

// Singleton NATS connection — created once on first use, drained in endThis()
let _nc = null;

async function getNatsConnection() {
  if (!_nc) {
    const { connect } = await import('nats');
    _nc = await connect({ servers: NATS_URL });
  }
  return _nc;
}

export async function logger(jsonData) {
  const payload = {
    ...jsonData,
    'samma-io': {
      scanner: SAMMA_IO_SCANNER,
      id: SAMMA_IO_ID,
      tags: SAMMA_IO_TAGS,
      json: SAMMA_IO_JSON,
    },
  };

  if (WRITE_TO_FILE !== 'False') {
    try {
      await mkdir(OUT_DIR, { recursive: true });
      await appendFile(path.join(OUT_DIR, PARSER + '.json'), JSON.stringify(payload) + '\n');
    } catch (err) {
      console.warn('sammaParser: file write failed:', err);
    }
  }

  if (NATS_ENABLED !== 'False') {
    try {
      const nc = await getNatsConnection();
      const { StringCodec } = await import('nats');
      const sc = StringCodec();
      await nc.publish(NATS_SUBJECT, sc.encode(JSON.stringify(payload)));
    } catch (err) {
      console.warn('sammaParser: NATS publish failed:', err);
      _nc = null; // reset so next call tries to reconnect
    }
  }

  console.log(JSON.stringify(payload));
}

export async function endThis() {
  await mkdir(OUT_DIR, { recursive: true });
  // Drain NATS connection if open
  if (_nc) {
    try { await _nc.drain(); } catch (_) {}
    _nc = null;
  }
  // Write completion signal (does not go through logger to avoid spurious findings)
  console.log(JSON.stringify({ scan: 'done' }));
  await writeFile(path.join(OUT_DIR, 'die'), 'time to die');
}
