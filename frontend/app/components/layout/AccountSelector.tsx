import React, { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getAccounts, getOverview, TradingAccount } from '@/lib/api'

interface Account {
  id: number
  user_id?: number
  username?: string
  name: string
  account_type: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
  model?: string
  is_active?: boolean
}

interface AccountWithAssets extends Account {
  total_assets: number
  positions_value: number
}

interface AccountSelectorProps {
  currentAccount: Account | null
  onAccountChange: (accountId: number) => void
  username?: string
  refreshTrigger?: number  // Add refresh trigger prop
}

// Use relative path to work with proxy
const API_BASE = '/api'

export default function AccountSelector({ currentAccount, onAccountChange, username = "default", refreshTrigger }: AccountSelectorProps) {
  const [accounts, setAccounts] = useState<AccountWithAssets[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAccounts()
  }, [username, refreshTrigger])  // Add refreshTrigger to dependency array

  const fetchAccounts = async () => {
    try {
      // Use default functions with hardcoded username for paper trading
      const accountData = await getAccounts()
      console.log('Fetched accounts:', accountData)
      
      // Get account-specific data for each account
      const accountsWithAssets: AccountWithAssets[] = await Promise.all(
        accountData.map(async (account) => {
          try {
            // Fetch overview data specific to this account
            const response = await fetch(`${API_BASE}/account/${account.id}/overview`)
            if (response.ok) {
              const accountOverview = await response.json()
              console.log(`Account ${account.id} overview:`, accountOverview)
              return {
                ...account,
                total_assets: accountOverview.total_assets || account.current_cash + account.frozen_cash,
                positions_value: accountOverview.positions_value || 0
              }
            } else {
              console.warn(`Failed to fetch overview for account ${account.id}:`, response.status, response.statusText)
              // Fallback to basic calculation if overview fails
              return {
                ...account,
                total_assets: account.current_cash + account.frozen_cash,
                positions_value: 0
              }
            }
          } catch (error) {
            console.warn(`Failed to fetch overview for account ${account.id}:`, error)
            // Fallback to basic calculation
            return {
              ...account,
              total_assets: account.current_cash + account.frozen_cash,
              positions_value: 0
            }
          }
        })
      )
      
      setAccounts(accountsWithAssets)
    } catch (error) {
      console.error('Error fetching accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-48">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  if (accounts.length === 0) {
    return (
      <div className="w-64">
        <div className="text-sm text-muted-foreground p-2 border rounded">
          No accounts found
        </div>
      </div>
    )
  }

  const displayName = (account: AccountWithAssets) => {
    const accountName = account.name || account.username || `${account.account_type} Account`
    return `${accountName} ($${account.total_assets.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`
  }

  // Find the current account in our loaded accounts list (which has total_assets)
  const currentAccountWithAssets = currentAccount 
    ? accounts.find(a => a.id === currentAccount.id) 
    : null

  return (
    <div className="w-full">
      <Select
        value={currentAccount?.id.toString() || ''}
        onValueChange={(value) => onAccountChange(parseInt(value))}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select Account" className="truncate">
            <span className="truncate block">
              {currentAccountWithAssets ? displayName(currentAccountWithAssets) : (currentAccount?.name || currentAccount?.username || 'Select Account')}
            </span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {accounts.map((account) => (
            <SelectItem key={account.id} value={account.id.toString()}>
              <div className="flex flex-col">
                <span className="font-medium">{displayName(account)}</span>
                <span className="text-xs text-muted-foreground">
                  Cash: ${account.current_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} | 
                  Positions: ${account.positions_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  {account.model && ` | ${account.model}`}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}