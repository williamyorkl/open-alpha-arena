// API configuration
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : '/api'  // Use proxy, don't hardcode port

// Helper function for making API requests
export async function apiRequest(
  endpoint: string, 
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }
  
  const response = await fetch(url, defaultOptions)
  
  if (!response.ok) {
    // Try to extract error message from response body
    try {
      const errorData = await response.json()
      const errorMessage = errorData.detail || errorData.message || `HTTP error! status: ${response.status}`
      throw new Error(errorMessage)
    } catch (e) {
      // If parsing fails, throw generic error
      throw new Error(`HTTP error! status: ${response.status}`)
    }
  }
  
  const contentType = response.headers.get('content-type')
  if (!contentType || !contentType.includes('application/json')) {
    throw new Error('Response is not JSON')
  }
  
  return response
}

// Specific API functions
export async function checkRequiredConfigs() {
  const response = await apiRequest('/config/check-required')
  return response.json()
}

// Crypto-specific API functions
export async function getCryptoSymbols() {
  const response = await apiRequest('/crypto/symbols')
  return response.json()
}

export async function getCryptoPrice(symbol: string) {
  const response = await apiRequest(`/crypto/price/${symbol}`)
  return response.json()
}

export async function getCryptoMarketStatus(symbol: string) {
  const response = await apiRequest(`/crypto/status/${symbol}`)
  return response.json()
}

export async function getPopularCryptos() {
  const response = await apiRequest('/crypto/popular')
  return response.json()
}

// AI Trader Account management functions
export interface AITraderAccount {
  id: number
  username: string  // Display name (e.g., "GPT", "Claude")
  model: string  // AI model (e.g., "gpt-4-turbo")
  base_url: string  // API endpoint
  api_key: string  // API key (masked in responses)
  initial_capital: number
  current_cash: number
  frozen_cash: number
}

export interface AITraderAccountCreate {
  username: string
  model: string
  base_url: string
  api_key: string
  initial_capital?: number
}

export interface AITraderAccountUpdate {
  username?: string
  model?: string
  base_url?: string
  api_key?: string
}

export async function listAITraderAccounts(): Promise<AITraderAccount[]> {
  const response = await apiRequest('/account/users')
  return response.json()
}

export async function createAITraderAccount(account: AITraderAccountCreate): Promise<AITraderAccount> {
  const response = await apiRequest('/account/users', {
    method: 'POST',
    body: JSON.stringify(account),
  })
  return response.json()
}

export async function updateAITraderAccount(accountId: number, account: AITraderAccountUpdate): Promise<AITraderAccount> {
  const response = await apiRequest(`/account/users/${accountId}`, {
    method: 'PUT',
    body: JSON.stringify(account),
  })
  return response.json()
}

export async function deleteAITraderAccount(accountId: number): Promise<void> {
  await apiRequest(`/account/users/${accountId}`, {
    method: 'DELETE',
  })
}

// Legacy aliases for backward compatibility
export type AIAccount = AITraderAccount
export type AIAccountCreate = AITraderAccountCreate
export const listAIAccounts = listAITraderAccounts
export const createAIAccount = createAITraderAccount
export const updateAIAccount = updateAITraderAccount
export const deleteAIAccount = deleteAITraderAccount