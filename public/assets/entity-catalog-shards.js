(() => {
  const nativeFetch = window.fetch.bind(window);
  const directEntityCatalog = /^\/data\/(genre|maker|actress)-catalog\/([^/]+)\.json$/;

  window.fetch = async (input, init) => {
    const requestUrl = typeof input === 'string' ? input : input?.url;
    if (!requestUrl) return nativeFetch(input, init);

    let url;
    try {
      url = new URL(requestUrl, location.href);
    } catch (_) {
      return nativeFetch(input, init);
    }

    const match = url.pathname.match(directEntityCatalog);
    if (!match) return nativeFetch(input, init);

    const response = await nativeFetch(input, init);
    if (!response.ok) return response;

    let manifest;
    try {
      manifest = await response.clone().json();
    } catch (_) {
      return response;
    }

    const shards = Array.isArray(manifest.shards) ? manifest.shards : [];
    if (!shards.length) return response;

    try {
      const payloads = await Promise.all(shards.map(async shard => {
        const file = typeof shard === 'string' ? shard : shard?.file;
        if (!file) return [];
        const shardResponse = await nativeFetch(file, {cache: 'no-cache'});
        if (!shardResponse.ok) throw new Error(`HTTP ${shardResponse.status}: ${file}`);
        const shardData = await shardResponse.json();
        return Array.isArray(shardData.items) ? shardData.items : [];
      }));

      const items = payloads.flat();
      if (Number(manifest.count || 0) && items.length !== Number(manifest.count)) {
        throw new Error(`Entity catalog shard count mismatch: expected=${manifest.count} actual=${items.length}`);
      }

      manifest.items = items;
      const headers = new Headers(response.headers);
      headers.set('content-type', 'application/json; charset=utf-8');
      headers.set('x-entity-catalog-sharded', '1');
      return new Response(JSON.stringify(manifest), {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    } catch (error) {
      console.warn('Sharded entity catalog load failed', error);
      return response;
    }
  };
})();
