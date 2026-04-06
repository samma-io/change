import { writeFile, appendFile, mkdir } from 'fs/promises';
import { connect, StringCodec } from 'nats';

const WRITE_TO_FILE = process.env.WRITE_TO_FILE ?? 'False';
const PARSER = process.env.PARSER ?? 'web-change-scanner';
const OUT_DIR = process.env.OUT_DIR ?? '/out';
const SAMMA_IO_SCANNER = process.env.SAMMA_IO_SCANNER ?? 'web-change-scanner';
const SAMMA_IO_ID = process.env.SAMMA_IO_ID ?? '1234';
const SAMMA_IO_TAGS = (process.env.SAMMA_IO_TAGS ?? 'scanner').split(',');
const SAMMA_IO_JSON = JSON.parse(process.env.SAMMA_IO_JSON ?? '{}');
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
    await mkdir(OUT_DIR, { recursive: true });
    await appendFile(`${OUT_DIR}/${PARSER}.json`, JSON.stringify(jsonData) + '\n');
  }

  if (NATS_ENABLED !== 'False') {
    const nc = await connect({ servers: NATS_URL });
    const sc = StringCodec();
    nc.publish(NATS_SUBJECT, sc.encode(JSON.stringify(jsonData)));
    await nc.drain();
  }

  console.log(JSON.stringify(jsonData));
}

export async function endThis() {
  await logger({ scan: 'done' });
  await writeFile(`${OUT_DIR}/die`, 'time to die');
}
