import AccountSelector from '@/components/layout/AccountSelector'

interface Account {
  id: number
  user_id: number
  name: string
  account_type: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
}

interface PortfolioProps {
  user: Account
  onUserChange?: (username: string) => void
}

export default function Portfolio({
  user,
  onUserChange
}: PortfolioProps) {
  return (
    <div className="space-y-6">
      {/* Account Selector */}
      {onUserChange && (
        <div className="flex justify-end">
          <AccountSelector
            currentAccount={user}
            onAccountChange={(accountId) => {
              console.log('Switch to account ID:', accountId)
              // Implement account switching if needed
            }}
          />
        </div>
      )}
    </div>
  )
}