export function courseGraphView(nodes, edges, confirmed = false) {
  const concepts = nodes.filter(node => node.kind === 'concept')
  const skills = nodes.filter(node => node.kind === 'skill').map(node => ({ ...node,
    assessment: node.assessment || node.mastery_standard, task: node.task || node.description }))
  const knowledgeIds = new Set(concepts.map(node => node.id))
  const skillIds = new Set(skills.map(node => node.id))
  const knowledgeLinks = edges.filter(edge => knowledgeIds.has(edge.source) && skillIds.has(edge.target))
    .map(edge => ({ knowledge_id: edge.source, skill_id: edge.target, relation: edge.relation }))
  return { status: confirmed ? 'approved_course' : 'ai_proposal',
    knowledge: { nodes: concepts, edges: edges.filter(edge => knowledgeIds.has(edge.source) && knowledgeIds.has(edge.target)) },
    skill: { nodes: skills, edges: edges.filter(edge => skillIds.has(edge.source) && skillIds.has(edge.target)), knowledge_links: knowledgeLinks } }
}
