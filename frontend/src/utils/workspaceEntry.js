export function hasWorkspaceTarget(query = {}) {
  return ['projectId', 'sessionId', 'localDraftId', 'testCase', 'pptFixture', 'pptGeneration', 'communityId']
    .some(key => String(query[key] ?? '').trim() !== '')
}

export function unwrapWorkspaceResult(response) {
  if (response?.code !== undefined && ![0, 200].includes(Number(response.code))) {
    throw new Error(response.message || '项目操作失败')
  }
  return response?.data ?? response
}
