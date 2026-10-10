/** Always release the generating button, including failed/aborted lazy imports. */
export async function navigateWorkspace(router, location, onSettled) {
  try {
    return await router.push(location)
  } finally {
    onSettled?.()
  }
}
