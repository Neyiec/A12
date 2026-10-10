// ws_page.page_title is VARCHAR(200). Full content remains in page_content.
export function persistedPageTitle(value, fallback = '') {
  const title = String(value ?? '').trim() || fallback
  const characters = Array.from(title)
  return characters.length > 200 ? characters.slice(0, 199).join('') + '…' : title
}
