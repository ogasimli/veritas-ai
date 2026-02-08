'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { z } from 'zod'

const fileSchema = z.object({
  name: z.string().endsWith('.docx', 'Only .docx files are allowed'),
  size: z.number().max(20 * 1024 * 1024, 'File must be less than 20MB'),
})

interface FileUploadZoneProps {
  label: string
  onFileChange: (file: File | null) => void
}

export function FileUploadZone({ label, onFileChange }: FileUploadZoneProps) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null)

      if (acceptedFiles.length === 0) {
        return
      }

      const droppedFile = acceptedFiles[0]

      // Validate with zod
      const result = fileSchema.safeParse({
        name: droppedFile.name,
        size: droppedFile.size,
      })

      if (!result.success) {
        setError(result.error.issues[0].message)
        setFile(null)
        onFileChange(null)
        return
      }

      setFile(droppedFile)
      onFileChange(droppedFile)
    },
    [onFileChange]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        ['.docx'],
    },
    maxFiles: 1,
    multiple: false,
  })

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <div
        {...getRootProps()}
        className={`
          relative flex min-h-[160px] cursor-pointer flex-col items-center justify-center
          rounded-lg border-2 border-dashed p-6 transition-all duration-200
          ${
            isDragActive
              ? 'border-blue-500 bg-blue-50 animate-pulse dark:bg-blue-900/20'
              : error
              ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
              : file
              ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
              : 'border-slate-300 bg-slate-50 hover:border-blue-500 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:hover:border-blue-500 dark:hover:bg-slate-700'
          }
        `}
      >
        <input {...getInputProps()} />

        {file ? (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-8 w-8 text-green-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {file.name}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-8 w-8 text-red-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            <p className="text-sm font-medium text-red-600 dark:text-red-400">
              {error}
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-8 w-8 text-slate-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {isDragActive ? 'Drop file here' : 'Drag & drop .docx file'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              or click to browse
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
