/* Poll helper: repeatedly call fn until condition met. */

export async function poll(fn, until, intervalMs, signal = null) {
  while (true) {
    if (signal?.aborted) throw new Error("Polling cancelled");

    const result = await fn();
    if (until(result)) return result;

    await new Promise((resolve) => {
      const timeoutId = setTimeout(resolve, intervalMs);
      if (signal) {
        signal.addEventListener(
          "abort",
          () => {
            clearTimeout(timeoutId);
            resolve();
          },
          { once: true }
        );
      }
    });
  }
}
