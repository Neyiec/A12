import test from 'node:test'
import assert from 'node:assert/strict'
import { pollStatus } from '../src/utils/statusPoller.js'

function setup(options = {}) {
  const queue = []
  let time = 0
  const stop = pollStatus({ request: async () => ({}), onResult: () => false,
    schedule: fn => { queue.push(fn); return fn }, unschedule: fn => {
      const i = queue.indexOf(fn); if (i >= 0) queue.splice(i, 1)
    }, now: () => time, ...options })
  return { queue, stop, advance: ms => { time += ms }, run: () => queue.shift()?.() }
}

test('slow requests never overlap and late results after unmount are ignored', async () => {
  let resolve, results = 0
  const p = setup({ request: () => new Promise(r => { resolve = r }), onResult: () => { results++; return false } })
  const pending = p.run()
  assert.equal(p.queue.length, 0)
  p.stop()
  resolve({})
  await pending
  assert.equal(results, 0)
  assert.equal(p.queue.length, 0)
})
test('terminal result stops subsequent requests', async () => {
  let stopped = 0
  const p = setup({ onResult: () => true, onStop: () => stopped++ })
  await p.run()
  assert.equal(stopped, 1)
  assert.equal(p.queue.length, 0)
})
test('auth failure stops immediately; transient failures stop at three', async () => {
  for (const status of [401, 403, 503]) {
    let failures = 0
    const p = setup({ request: async () => { throw { response: { status } } }, onError: () => failures++ })
    await p.run()
    if (status === 503) { assert.equal(failures, 0); await p.run(); await p.run() }
    assert.equal(failures, 1)
    assert.equal(p.queue.length, 0)
  }
})
test('wall clock deadline stops polling and successful queries reset failure count', async () => {
  let calls = 0, failures = 0, timedOut = 0
  const p = setup({ request: async () => { if (++calls !== 2) throw new Error('network'); return {} },
    onError: () => failures++, onTimeout: () => timedOut++ })
  for (let i = 0; i < 4; i++) await p.run()
  assert.equal(failures, 0)
  p.advance(600000)
  await p.run()
  assert.equal(timedOut, 1)
  assert.equal(p.queue.length, 0)
})
