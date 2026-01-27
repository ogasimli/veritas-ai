import { Parser } from 'json2csv'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import type { AgentResult } from './types'

export function exportToCSV(results: AgentResult[]) {
  const findings = results.filter(r => !r.error)

  if (findings.length === 0) {
    alert('No findings to export')
    return
  }

  try {
    // Transform findings to flat structure for CSV
    const data = findings.map((finding) => ({
      agent: finding.agent,
      severity: finding.severity,
      title: finding.title,
      description: finding.description,
    }))

    // Create CSV using json2csv Parser
    const parser = new Parser({
      fields: ['agent', 'severity', 'title', 'description'],
    })
    const csv = parser.parse(data)

    // Create Blob and trigger download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit-findings-${new Date().toISOString()}.csv`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('CSV export error:', error)
    alert('Failed to export CSV. Please try again.')
  }
}

export function exportToPDF(results: AgentResult[]) {
  const findings = results.filter(r => !r.error)

  if (findings.length === 0) {
    alert('No findings to export')
    return
  }

  try {
    // Create new jsPDF instance
    const doc = new jsPDF()

    // Add title
    doc.setFontSize(18)
    doc.text('Audit Findings Report', 14, 20)

    // Add timestamp
    doc.setFontSize(11)
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 28)

    // Prepare table data
    const tableData = findings.map((finding) => [
      finding.agent || '',
      finding.severity || '',
      finding.title || '',
      finding.description || '',
    ])

    // Add table using autoTable
    autoTable(doc, {
      head: [['Agent', 'Severity', 'Title', 'Description']],
      body: tableData,
      startY: 35,
      styles: { fontSize: 9 },
      headStyles: { fillColor: [71, 85, 105] },
      columnStyles: {
        0: { cellWidth: 30 },
        1: { cellWidth: 25 },
        2: { cellWidth: 45 },
        3: { cellWidth: 90 },
      },
    })

    // Save PDF
    doc.save(`audit-findings-${new Date().toISOString()}.pdf`)
  } catch (error) {
    console.error('PDF export error:', error)
    alert('Failed to export PDF. Please try again.')
  }
}
