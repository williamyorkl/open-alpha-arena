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

// User authentication interfaces
export interface User {
  id: number
  username: string
  email?: string
  is_active: boolean
}

export interface UserCreate {
  username: string
  email?: string
  password?: string
}

export interface UserAuthResponse {
  user: User
  session_token: string
  expires_at: string
}

// Trading Account management functions
export interface TradingAccount {
  id: number
  user_id: number
  name: string  // Display name (e.g., "GPT Trader", "Claude Analyst")
  model?: string  // AI model (e.g., "gpt-4-turbo")
  base_url?: string  // API endpoint
  api_key?: string  // API key (masked in responses)
  initial_capital: number
  current_cash: number
  frozen_cash: number
  account_type: string  // "AI" or "MANUAL"
  is_active: boolean
}

export interface TradingAccountCreate {
  name: string
  model?: string
  base_url?: string
  api_key?: string
  initial_capital?: number
  account_type?: string
}

export interface TradingAccountUpdate {
  name?: string
  model?: string
  base_url?: string
  api_key?: string
}

// User authentication functions
export async function registerUser(userData: UserCreate): Promise<User> {
  const response = await apiRequest('/users/register', {
    method: 'POST',
    body: JSON.stringify(userData),
  })
  return response.json()
}

export async function loginUser(username: string, password: string): Promise<UserAuthResponse> {
  const response = await apiRequest('/users/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  return response.json()
}

export async function getUserProfile(sessionToken: string): Promise<User> {
  const response = await apiRequest(`/users/profile?session_token=${sessionToken}`)
  return response.json()
}

// Trading Account management functions (matching backend query parameter style)
export async function listTradingAccounts(sessionToken: string): Promise<TradingAccount[]> {
  const response = await apiRequest(`/accounts/?session_token=${sessionToken}`)
  return response.json()
}

export async function createTradingAccount(account: TradingAccountCreate, sessionToken: string): Promise<TradingAccount> {
  const response = await apiRequest(`/accounts/?session_token=${sessionToken}`, {
    method: 'POST',
    body: JSON.stringify(account),
  })
  return response.json()
}

export async function updateTradingAccount(accountId: number, account: TradingAccountUpdate, sessionToken: string): Promise<TradingAccount> {
  const response = await apiRequest(`/accounts/${accountId}?session_token=${sessionToken}`, {
    method: 'PUT',
    body: JSON.stringify(account),
  })
  return response.json()
}

export async function deleteTradingAccount(accountId: number, sessionToken: string): Promise<void> {
  await apiRequest(`/accounts/${accountId}?session_token=${sessionToken}`, {
    method: 'DELETE',
  })
}

// Demo mode functions (no authentication required)
export async function initDemoUser(username: string = "demo"): Promise<{user: User, account: TradingAccount}> {
  const response = await apiRequest(`/demo/init?username=${username}`)
  return response.json()
}

export async function getDemoAccounts(username: string = "demo"): Promise<TradingAccount[]> {
  const response = await apiRequest(`/demo/accounts?username=${username}`)
  return response.json()
}

export async function getDemoOverview(username: string = "demo"): Promise<any> {
  const response = await apiRequest(`/demo/overview?username=${username}`)
  return response.json()
}

export async function resetDemoAccount(username: string = "demo"): Promise<any> {
  const response = await apiRequest(`/demo/reset?username=${username}`, {
    method: 'POST'
  })
  return response.json()
}

// Legacy aliases for backward compatibility
export type AIAccount = TradingAccount
export type AIAccountCreate = TradingAccountCreate

// Updated legacy functions to use demo mode for simulation
export const listAIAccounts = () => getDemoAccounts("demo")
export const createAIAccount = (account: any) => {
  console.warn("createAIAccount is deprecated. Use demo mode or new trading account APIs.")
  return Promise.resolve({} as TradingAccount)
}
export const updateAIAccount = (id: number, account: any) => {
  console.warn("updateAIAccount is deprecated. Use demo mode or new trading account APIs.")
  return Promise.resolve({} as TradingAccount)
}
export const deleteAIAccount = (id: number) => {
  console.warn("deleteAIAccount is deprecated. Use demo mode or new trading account APIs.")
  return Promise.resolve()
}