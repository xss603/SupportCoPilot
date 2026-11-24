import test from 'node:test';
import assert from 'node:assert/strict';
import { runbookSearch } from '../src/docs/runbookSearch.js';

test('RunbookSearcher loads markdown runbooks and matches keywords', async () => {
  const result = await runbookSearch.searchRelevantContext('502 bad gateway istio mtls ingress');
  assert.match(result, /502 Bad Gateway/i);
  assert.match(result, /DestinationRule/i);
  assert.match(result, /ISTIO_MUTUAL/i);
});

test('RunbookSearcher returns database runbook on postgres grant queries', async () => {
  const result = await runbookSearch.searchRelevantContext('request grant all permissions on postgres database');
  assert.match(result, /Database/i);
  assert.match(result, /schema/i);
});
