/** 统一请求封装：拼后端地址、抛网络错误、给页脚留一句可读的说明。 */
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export function request(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  return fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  }).catch((error: unknown) => {
    const detail = error instanceof Error ? error.message : '请求未送达'
    throw new Error(`接口请求失败：${detail}`)
  })
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(`接口返回 ${response.status}，数据未更新`)
  }
  return (await response.json()) as T
}

/** 带重试的读取：接口偶发失败时自动补几次，仍失败就把最后一次错误抛给页面。 */
export async function fetchJsonWithRetry<T>(path: string, attempts = 3): Promise<T> {
  let lastError: unknown = new Error('接口请求失败')
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await fetchJson<T>(path)
    } catch (error) {
      lastError = error
      if (attempt < attempts - 1) {
        await new Promise((resolve) => setTimeout(resolve, 300 * (attempt + 1)))
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error('接口请求失败')
}
