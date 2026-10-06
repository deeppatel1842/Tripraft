// Purpose: Deduplicates message IDs across cached pages and reconciles optimistic send results.
export const pageMessages = page => page?.data?.messages ?? page?.messages ?? [];
const withMessages = (page, messages) => page?.data ? { ...page, data: { ...page.data, messages } } : { ...page, messages };
export function removeMessage(cache, id) {
  if (!cache?.pages) return cache;
  return { ...cache, pages: cache.pages.map(p => withMessages(p, pageMessages(p).filter(m => String(m.id) !== String(id)))) };
}
export function mergeMessage(cache, message) {
  if (!message?.id) return cache;
  if (!cache?.pages?.length) return { pages: [{ data: { messages: [message], has_more: false } }], pageParams: [undefined] };
  if (cache.pages.some(p => pageMessages(p).some(m => String(m.id) === String(message.id)))) return cache;
  const first = cache.pages[0];
  return { ...cache, pages: [withMessages(first, [message, ...pageMessages(first)]), ...cache.pages.slice(1)] };
}
