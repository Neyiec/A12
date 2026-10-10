/** Keep the SSE graph payload at message.data, the shape consumed by LearningGraphPanel. */
export function upsertLearningGraphMessage(messages, graphs, activeId, addMessage) {
  if (!Array.isArray(graphs?.knowledge?.nodes) || !Array.isArray(graphs?.skill?.nodes)) return activeId
  const existing = activeId == null ? null : messages.find((message) => message.id === activeId)
  if (existing) {
    existing.data = graphs
    return activeId
  }
  const message = addMessage('assistant', 'learning_graph', '', graphs)
  return message?.id ?? messages[messages.length - 1]?.id ?? null
}
