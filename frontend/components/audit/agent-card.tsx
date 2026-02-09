'use client'

import { useState, useEffect } from 'react'
import type { AgentStatus, AgentResult } from '@/lib/types'

const AGENT_LOADING_MESSAGES: Record<string, string[]> = {
  numeric: [
    'Recalculating totals and verifying arithmetic across tables...',
    'Cross-checking reported figures against source data...',
    'Hunting for rounding errors and mismatched sums...',
    'Validating percentage calculations and ratio accuracy...',
    'Tracing numbers through footnotes and appendices...',
    'Comparing year-over-year figures for numerical consistency...',
    'Auditing decimal precision across financial statements...',
    'Reconciling line items to ensure the numbers add up...',
    'Stress-testing calculations — every digit matters...',
    'Scanning for transposition errors and data-entry anomalies...',
  ],
  logic: [
    'Checking narrative claims against the underlying data...',
    'Evaluating whether conclusions logically follow the evidence...',
    'Spotting contradictions between sections of the report...',
    'Analyzing if forward-looking statements align with historical trends...',
    'Reviewing cause-and-effect reasoning for logical soundness...',
    'Comparing qualitative assertions with quantitative results...',
    'Detecting inconsistencies between the summary and detailed findings...',
    'Assessing whether assumptions are internally consistent...',
    'Tracing logical flow from premises to reported conclusions...',
    'Evaluating coherence of the overall narrative structure...',
  ],
  disclosure: [
    'Reviewing required disclosures against regulatory checklists...',
    'Checking for missing risk factors and material omissions...',
    'Verifying footnote completeness and accuracy...',
    'Scanning for compliance with reporting standards...',
    'Assessing whether related-party transactions are fully disclosed...',
    'Validating that accounting policy changes are properly noted...',
    'Checking segment reporting for adequate transparency...',
    'Reviewing contingent liability disclosures for completeness...',
    'Ensuring off-balance-sheet items are properly reported...',
    'Auditing disclosure language against regulatory requirements...',
  ],
  external: [
    'Cross-referencing claims against public market data...',
    'Scanning news sources for corroborating information...',
    'Comparing reported metrics with industry benchmarks...',
    'Checking filings against publicly available records...',
    'Validating external references and cited data sources...',
    'Surveying analyst reports for conflicting viewpoints...',
    'Matching reported figures against regulatory filings...',
    'Searching for relevant press releases and announcements...',
    'Benchmarking performance claims against peer companies...',
    'Gathering external signals to verify key assertions...',
  ],
}

const AGENT_CONFIG = {
  numeric: {
    label: 'Numeric Validation',
    icon: 'calculate',
    color: 'blue',
  },
  logic: {
    label: 'Logic Consistency',
    icon: 'account_tree',
    color: 'purple',
  },
  disclosure: {
    label: 'Disclosure Compliance',
    icon: 'policy',
    color: 'orange',
  },
  external: {
    label: 'External Signals',
    icon: 'public',
    color: 'teal',
  },
} as const

const COLOR_CLASSES = {
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
    icon: 'text-blue-500',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    dot: 'bg-blue-500 dark:bg-blue-400',
  },
  purple: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    text: 'text-purple-700 dark:text-purple-300',
    icon: 'text-purple-500',
    badge: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    dot: 'bg-purple-500 dark:bg-purple-400',
  },
  orange: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    border: 'border-orange-200 dark:border-orange-800',
    text: 'text-orange-700 dark:text-orange-300',
    icon: 'text-orange-500',
    badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    dot: 'bg-orange-500 dark:bg-orange-400',
  },
  teal: {
    bg: 'bg-teal-50 dark:bg-teal-900/20',
    border: 'border-teal-200 dark:border-teal-800',
    text: 'text-teal-700 dark:text-teal-300',
    icon: 'text-teal-500',
    badge: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
    dot: 'bg-teal-500 dark:bg-teal-400',
  },
}

const SEVERITY_COLORS = {
  critical: 'border-red-500',
  warning: 'border-amber-500',
  pass: 'border-green-500',
}

interface AgentCardProps {
  agent: keyof typeof AGENT_CONFIG
  status: AgentStatus['status']
  results: AgentResult[]
}

export function AgentCard({ agent, status, results }: AgentCardProps) {
  const config = AGENT_CONFIG[agent]
  const colors = COLOR_CLASSES[config.color]

  // Shuffle messages once per mount for this agent
  const [messages] = useState(() =>
    [...AGENT_LOADING_MESSAGES[agent]].sort(() => Math.random() - 0.5)
  )

  // Message rotation for processing state
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (status !== 'processing') return
    const interval = setInterval(() => {
      setTick(prev => prev + 1)
    }, 5000)
    return () => clearInterval(interval)
  }, [status])

  const currentMessage = messages[tick % messages.length]

  // Find error result if any
  const errorResult = results.find(r => r.error)
  const findings = results.filter(r => !r.error && (r.title || r.description))

  return (
    <div
      className={`flex max-h-[600px] flex-col rounded-lg border ${colors.border} ${colors.bg} overflow-hidden shadow-sm transition-shadow duration-200 hover:shadow-md`}
    >
      {/* Header */}
      <div className={`shrink-0 border-b ${colors.border} p-4`}>
        <div className="flex items-center gap-2">
          <span className={`material-icons ${colors.icon}`}>{config.icon}</span>
          <h3 className={`font-semibold ${colors.text}`}>{config.label}</h3>
          {status === 'complete' && findings.length > 0 && (
            <span className={`ml-auto rounded-full px-2 py-0.5 text-xs font-medium ${colors.badge}`}>
              {findings.length}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {status === 'processing' && (
          <div className="flex items-center justify-center py-8">
            <div className="flex w-full max-w-[260px] flex-col items-center gap-3">
              {/* Thinking dots */}
              <div className="flex items-center gap-2">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className={`h-2 w-2 rounded-full ${colors.dot}`}
                    style={{
                      animation: 'thinkingDot 1.4s ease-in-out infinite',
                      animationDelay: `${i * 0.2}s`,
                    }}
                  />
                ))}
              </div>

              {/* Loading message */}
              <p
                key={currentMessage}
                className="text-center text-sm leading-relaxed text-slate-600 dark:text-slate-400"
                style={{ animation: 'messageFadeIn 0.5s ease-out' }}
              >
                {currentMessage}
              </p>
            </div>
          </div>
        )}

        {status === 'complete' && findings.length === 0 && (
          <div className="flex items-center gap-2 py-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-5 w-5 text-green-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              No issues found
            </p>
          </div>
        )}

        {status === 'complete' && findings.length > 0 && (
          <div className="space-y-3">
            {findings.map((finding, index) => (
              <div
                key={finding.id}
                className={`border-l-4 ${SEVERITY_COLORS[finding.severity || 'pass']} rounded-r bg-white p-3 shadow-sm transition-all duration-200 hover:shadow-md dark:bg-slate-800`}
                style={{
                  animation: `fadeIn 0.3s ease-in-out ${index * 0.1}s both`,
                }}
              >
                <h4 className="text-sm font-medium text-slate-900 dark:text-white">
                  {finding.title || 'Untitled Finding'}
                </h4>
                <p className="mt-1 whitespace-pre-line text-xs text-slate-600 dark:text-slate-400">
                  {finding.description}
                </p>
              </div>
            ))}
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 py-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-5 w-5 text-red-500"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
              <p className="text-sm font-medium text-red-600 dark:text-red-400">
                Processing failed
              </p>
            </div>
            {errorResult && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-900 dark:border-red-900 dark:bg-red-900/20 dark:text-red-200">
                <p className="mt-1">{errorResult.error}</p>
              </div>
            )}
          </div>
        )}

        {status === 'idle' && (
          <div className="py-4 text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Waiting to start...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
