interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

function normalizeBaseUrl(value?: string): string {
  return value?.trim().replace(/\/$/, '') ?? ''
}

export function getApiBaseUrl(): string {
  const configuredBaseUrl = normalizeBaseUrl((import.meta as unknown as ImportMeta).env.VITE_API_BASE_URL)
  return configuredBaseUrl ? `${configuredBaseUrl}/api/v1` : '/api/v1'
}

export function getBackendUrl(path: string): string {
  const configuredBaseUrl = normalizeBaseUrl((import.meta as unknown as ImportMeta).env.VITE_API_BASE_URL)
  if (!configuredBaseUrl) {
    return path.startsWith('/') ? path : `/${path}`
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${configuredBaseUrl}${normalizedPath}`
}
