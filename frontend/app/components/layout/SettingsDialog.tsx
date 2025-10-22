import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Plus, Pencil } from 'lucide-react'
import { 
  getAccounts as getAccounts,
  createAccount as createAccount,
  updateAccount as updateAccount,
  type TradingAccount,
  type TradingAccountCreate,
  type TradingAccountUpdate
} from '@/lib/api'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface AIAccount extends TradingAccount {
  model?: string
  base_url?: string
  api_key?: string
}

interface AIAccountCreate extends TradingAccountCreate {
  model?: string
  base_url?: string
  api_key?: string
}

export default function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [accounts, setAccounts] = useState<AIAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [newAccount, setNewAccount] = useState<AIAccountCreate>({
    name: '',
    model: '',
    base_url: '',
    api_key: 'default-key-please-update-in-settings',
  })
  const [editAccount, setEditAccount] = useState<AIAccountCreate>({
    name: '',
    model: '',
    base_url: '',
    api_key: 'default-key-please-update-in-settings',
  })

  const loadAccounts = async () => {
    try {
      setLoading(true)
      const data = await getAccounts()
      setAccounts(data)
    } catch (error) {
      console.error('Failed to load accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadAccounts()
      setError(null)
      setShowAddForm(false)
      setEditingId(null)
    }
  }, [open])

  const handleCreateAccount = async () => {
    try {
      setLoading(true)
      setError(null)
      
      if (!newAccount.name || !newAccount.name.trim()) {
        setError('Account name is required')
        setLoading(false)
        return
      }
      
      console.log('Creating account with data:', newAccount)
      await createAccount(newAccount)
      setNewAccount({ name: '', model: '', base_url: '', api_key: 'default-key-please-update-in-settings' })
      setShowAddForm(false)
      await loadAccounts()
    } catch (error) {
      console.error('Failed to create account:', error)
      setError(error instanceof Error ? error.message : 'Failed to create account')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateAccount = async () => {
    if (!editingId) return
    try {
      setLoading(true)
      setError(null)
      
      if (!editAccount.name || !editAccount.name.trim()) {
        setError('Account name is required')
        setLoading(false)
        return
      }
      
      console.log('Updating account with data:', editAccount)
      await updateAccount(editingId, editAccount)
      setEditingId(null)
      setEditAccount({ name: '', model: '', base_url: '', api_key: '' })
      await loadAccounts()
    } catch (error) {
      console.error('Failed to update account:', error)
      setError(error instanceof Error ? error.message : 'Failed to update account')
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (account: AIAccount) => {
    setEditingId(account.id)
    setEditAccount({
      name: account.name,
      model: account.model || '',
      base_url: account.base_url || '',
      api_key: account.api_key || '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditAccount({ name: '', model: '', base_url: '', api_key: 'default-key-please-update-in-settings' })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Account Management</DialogTitle>
          <DialogDescription>
            Manage your trading accounts and AI configurations
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="space-y-6">
          {/* Existing Accounts */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">Trading Accounts</h3>
              <Button
                onClick={() => setShowAddForm(!showAddForm)}
                size="sm"
                className="flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Account
              </Button>
            </div>

            {loading && accounts.length === 0 ? (
              <div>Loading accounts...</div>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <div key={account.id} className="border rounded-lg p-4">
                    {editingId === account.id ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <Input
                            placeholder="Account name"
                            value={editAccount.name || ''}
                            onChange={(e) => setEditAccount({ ...editAccount, name: e.target.value })}
                          />
                          <Input
                            placeholder="Model"
                            value={editAccount.model || ''}
                            onChange={(e) => setEditAccount({ ...editAccount, model: e.target.value })}
                          />
                        </div>
                        <Input
                          placeholder="Base URL"
                          value={editAccount.base_url || ''}
                          onChange={(e) => setEditAccount({ ...editAccount, base_url: e.target.value })}
                        />
                        <Input
                          placeholder="API Key"
                          type="password"
                          value={editAccount.api_key || ''}
                          onChange={(e) => setEditAccount({ ...editAccount, api_key: e.target.value })}
                        />
                        <div className="flex gap-2">
                          <Button onClick={handleUpdateAccount} disabled={loading} size="sm">
                            Save
                          </Button>
                          <Button onClick={cancelEdit} variant="outline" size="sm">
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="space-y-1 flex-1">
                          <div className="font-medium">{account.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {account.model ? `Model: ${account.model}` : 'No model configured'}
                          </div>
                          {account.base_url && (
                            <div className="text-sm text-muted-foreground truncate">
                              Base URL: {account.base_url}
                            </div>
                          )}
                          {account.api_key && (
                            <div className="text-sm text-muted-foreground">
                              API Key: {'*'.repeat(Math.max(0, (account.api_key?.length || 0) - 4))}{account.api_key?.slice(-4) || '****'}
                            </div>
                          )}
                          <div className="text-sm text-muted-foreground">
                            Cash: ${account.current_cash?.toLocaleString() || '0'}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => startEdit(account)}
                            variant="outline"
                            size="sm"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add New Account Form */}
          {showAddForm && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="text-lg font-medium">Add New Account</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    placeholder="Account name"
                    value={newAccount.name || ''}
                    onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
                  />
                  <Input
                    placeholder="Model (e.g., gpt-4)"
                    value={newAccount.model || ''}
                    onChange={(e) => setNewAccount({ ...newAccount, model: e.target.value })}
                  />
                </div>
                <Input
                  placeholder="Base URL (e.g., https://api.openai.com/v1)"
                  value={newAccount.base_url || ''}
                  onChange={(e) => setNewAccount({ ...newAccount, base_url: e.target.value })}
                />
                <Input
                  placeholder="API Key"
                  type="password"
                  value={newAccount.api_key || ''}
                  onChange={(e) => setNewAccount({ ...newAccount, api_key: e.target.value })}
                />
                <div className="flex gap-2">
                  <Button onClick={handleCreateAccount} disabled={loading}>
                    Create Account
                  </Button>
                  <Button 
                    onClick={() => setShowAddForm(false)} 
                    variant="outline"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}