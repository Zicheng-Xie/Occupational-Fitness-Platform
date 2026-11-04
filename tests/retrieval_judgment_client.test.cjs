/* Regression tests for the static-preview failure and visible model commentary. */
const test = require('node:test');
const assert = require('node:assert/strict');
const client = require('../src/occupational_fitness_rag/web/static/retrieval_judgment.js');

test('file-server ENOENT is explained without a JSON syntax error', async () => {
  const response = new Response("Error: ENOENT: no such file or directory, open '/api/review-models'", {status: 404});
  await assert.rejects(client.readJsonResponse(response), error =>
    error.code === 'wrong_service' && error.message.includes('live assessment service') &&
    !error.message.includes('Unexpected token'));
});

test('a valid review response retains the actual model explanation', async () => {
  const result = await client.readJsonResponse(new Response(JSON.stringify({result: {
    fitness: 'undetermined', outcome: 'insufficient_information',
    explanation: 'The original evidence requires a completed investigation.'
  }})));
  const html = client.decisionSummary(result.result);
  assert.match(html, /Model decision/);
  assert.match(html, /Model explanation/);
  assert.match(html, /The original evidence requires a completed investigation\./);
});

test('live link keeps the exact screenshot condition when opened from a preview', () => {
  const condition = {dataset: 'refinement', query_id: 'BLACKOUT-QUERY', method: 'hybrid',
    top_k: 10, model: 'llama3:8b', evidence_mode: 'strict_topk'};
  const url = new URL(client.liveReviewURL('refinement', condition));
  assert.equal(url.origin, 'http://127.0.0.1:8781');
  for (const [key, value] of Object.entries(condition)) assert.equal(url.searchParams.get(key), String(value));
});

test('a different Top K or model cannot be substituted for a saved review', () => {
  const condition = {dataset: 'refinement', query_id: 'Q', method: 'hybrid', top_k: 10,
    model: 'llama3:8b', evidence_mode: 'strict_topk'};
  const records = [{condition: {...condition, top_k: 5}, result: {explanation: 'Wrong K'}},
    {condition, result: {explanation: 'Actual Top 10 review'}}];
  assert.equal(client.savedReview(records, condition).result.explanation, 'Actual Top 10 review');
  assert.equal(client.savedReview(records, {...condition, model: 'other-model'}), undefined);
});

test('model HTML is rendered as text', () => {
  const html = client.decisionSummary({fitness: 'no', outcome: 'temporarily_unfit',
    explanation: '<script>malicious()</script>'});
  assert.ok(!html.includes('<script>'));
  assert.match(html, /&lt;script&gt;/);
});

test('polling continues while a single validation repair is running', () => {
  assert.equal(client.isPendingReview({status: 'repairing'}), true);
  assert.equal(client.isPendingReview({status: 'failed'}), false);
  assert.equal(client.isPendingReview({status: 'completed'}), false);
});

test('a successful retry replaces the failed result for the same condition', () => {
  const condition = {query_id: 'Q', top_k: 10};
  const records = [{id: 'failed', condition, status: 'failed'},
    {id: 'retried', condition, status: 'completed', result: {explanation: 'Actual repaired response'}}];
  assert.equal(client.savedReview(records, condition).id, 'retried');
});
