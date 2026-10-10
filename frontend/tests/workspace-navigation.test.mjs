import test from 'node:test'
import assert from 'node:assert/strict'
import { navigateWorkspace } from '../src/utils/workspaceNavigation.js'

test('failed lazy import resets generating state and propagates the error for the UI', async () => {
  let loading = true
  const failure = new TypeError('Failed to fetch dynamically imported module')
  const router = { push: async () => { throw failure } }
  await assert.rejects(navigateWorkspace(router, { path: '/main/workspace' }, () => { loading = false }), error => error === failure)
  assert.equal(loading, false)
})

test('loading stays active until navigation finishes; success and abort both release it', async () => {
  for (const result of [undefined, { type: 4 }]) {
    let finish
    let loading = true
    const router = { push: () => new Promise(resolve => { finish = resolve }) }
    const pending = navigateWorkspace(router, { path: '/main/workspace' }, () => { loading = false })
    assert.equal(loading, true)
    finish(result)
    assert.equal(await pending, result)
    assert.equal(loading, false)
  }
})
