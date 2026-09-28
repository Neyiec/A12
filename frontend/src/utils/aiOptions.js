export const normalizeModelProfile = (value) => ['fast', 'standard', 'deep'].includes(value) ? value : 'standard'

export const normalizeReasoningEffort = (value) => ['low', 'medium', 'high'].includes(value) ? value : 'medium'
