import { writeFile, appendFile, mkdir } from 'fs/promises';
import { connect, StringCodec } from 'nats';
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

export async function logger(jsonData) {
  jsonData['samma-io'] = {
    scanner: SAMMA_IO_SCANNER,
    id: SAMMA_IO_ID,
    tags: SAMMA_IO_TAGS,
    json: SAMMA_IO_JSON,
  };

  if (WRITE_TO_FILE !== 'False') {
    try {
      await mkdir(OUT_DIR, { recursive: true });
      await appendFile(path.join(OUT_DIR, PARSER + '.json'), JSON.stringify(jsonData) + '\n');
    } catch (err) {
      console.warn('sammaParser: file write failed:', err);
    }
  }

  if (NATS_ENABLED !== 'False') {
    let nc;
    try {
      nc = await connect({ servers: NATS_URL });
      const sc = StringCodec();
      await nc.publish(NATS_SUBJECT, sc.encode(JSON.stringify(jsonData)));
    } catch (err) {
      console.warn('sammaParser: NATS publish failed:', err);
    } finally {
      if (nc) {
        await nc.drain();
      }
    }
  }

  console.log(JSON.stringify(jsonData));
}

export async function endThis() {
  await mkdir(OUT_DIR, { recursive: true });
  try {
    await logger({ scan: 'done' });
  } catch (err) {
    console.warn('sammaParser: logger failed in endThis:', err);
  }
  await writeFile(path.join(OUT_DIR, 'die'), 'time to die');
}
