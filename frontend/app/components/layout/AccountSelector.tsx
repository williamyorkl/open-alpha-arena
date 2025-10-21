import React, { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getDemoAccounts, getDemoOverview, TradingAccount } from '@/lib/api'

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
}

// Use relative path to work with proxy
const API_BASE = '/api'

export default function AccountSelector({ currentAccount, onAccountChange, username = "demo" }: AccountSelectorProps) {
  const [accounts, setAccounts] = useState<AccountWithAssets[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAccounts()
  }, [username])

  const fetchAccounts = async () => {
    try {
      // Use demo mode API for simulation
      const accountData = await getDemoAccounts(username)
      console.log('Fetched accounts:', accountData)
      
      // Fetch overview data to get total_assets
      const overview = await getDemoOverview(username)
      
      // Map accounts with assets info
      const accountsWithAssets: AccountWithAssets[] = accountData.map(account => ({
        ...account,
        total_assets: overview.portfolio?.total_assets || account.current_cash + account.frozen_cash,
        positions_value: overview.portfolio?.positions_value || 0
      }))
      
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