'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { fetchAudits, updateAudit, deleteAudit } from '@/lib/api'
import { type Audit } from '@/lib/types'
import { Trash2, Pencil, Check, X } from 'lucide-react'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'

export function AuditList() {
  const router = useRouter()
  const pathname = usePathname()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const { data: audits, isLoading } = useQuery({
    queryKey: ['audits'],
    queryFn: fetchAudits,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      updateAudit(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audits'] })
      setEditingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAudit,
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['audits'] })

      // If we deleted the currently active audit, navigate to the top-most remaining one
      if (pathname === `/audit/${deletedId}`) {
        const remainingAudits = audits?.filter(a => a.id !== deletedId) || []
        if (remainingAudits.length > 0) {
          router.push(`/audit/${remainingAudits[0].id}`)
        } else {
          router.push('/audit/new')
        }
      }
    },
  })

  const handleStartEdit = (e: React.MouseEvent, audit: Audit) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingId(audit.id)
    setEditName(audit.name)
  }

  const handleSaveEdit = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (editingId && editName.trim()) {
      updateMutation.mutate({ id: editingId, name: editName })
    }
  }

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingId(null)
  }

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    setDeleteId(id)
  }

  const confirmDelete = () => {
    if (deleteId) {
      deleteMutation.mutate(deleteId)
      setDeleteId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800"
          />
        ))}
      </div>
    )
  }

  if (!audits || audits.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No audits yet
        </p>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      complete: {
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-700 dark:text-green-400',
        border: 'border-green-500',
      },
      processing: {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-700 dark:text-blue-400',
        border: 'border-blue-500',
      },
      error: {
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-700 dark:text-red-400',
        border: 'border-red-500',
      },
      draft: {
        bg: 'bg-slate-100 dark:bg-slate-800',
        text: 'text-slate-600 dark:text-slate-400',
        border: 'border-slate-300',
      },
    }
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.draft
    return (
      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${config.bg} ${config.text} ${config.border}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="space-y-2">
      {audits.map((audit) => {
        const isActive = pathname === `/audit/${audit.id}`
        const isEditing = editingId === audit.id

        return (
          <Link
            key={audit.id}
            href={`/audit/${audit.id}`}
            className={`group relative block rounded-lg border-l-4 px-4 py-3 transition-all duration-200 ${isActive
              ? 'border-blue-500 bg-blue-50 shadow-sm dark:bg-blue-900/20'
              : 'border-transparent bg-white hover:border-slate-300 hover:bg-slate-50 hover:shadow-sm dark:bg-slate-900 dark:hover:bg-slate-800'
              }`}
          >
            <div className="flex items-center justify-between gap-2">
              {isEditing ? (
                <div className="flex flex-1 items-center gap-2" onClick={(e) => e.preventDefault()}>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-8 w-full rounded border border-slate-300 px-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button
                    onClick={handleSaveEdit}
                    className="rounded p-1 text-green-600 hover:bg-green-100 dark:text-green-400 dark:hover:bg-green-900/30"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="rounded p-1 text-red-600 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <span className="truncate font-medium text-slate-900 dark:text-white">
                  {audit.name}
                </span>
              )}

              {!isEditing && (
                <div className="flex items-center gap-2">
                  {getStatusBadge(audit.status)}
                  <div className="opacity-0 transition-opacity group-hover:opacity-100 flex items-center gap-1">
                    <button
                      onClick={(e) => handleStartEdit(e, audit)}
                      className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteClick(e, audit.id)}
                      className="rounded p-1 text-slate-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </Link>
        )
      })}

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={confirmDelete}
        title="Delete Audit"
        description="Are you sure you want to delete this audit? This action cannot be undone."
        confirmText="Delete"
        variant="danger"
      />
    </div >
  )
}
