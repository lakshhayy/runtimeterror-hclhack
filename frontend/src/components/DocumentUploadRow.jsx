import { useState } from 'react'
import toast from 'react-hot-toast'
import { CheckCircle2, Upload } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Button from './Button'

const DOC_HINTS = {
  IDENTITY: 'PAN or Aadhaar',
  ADDRESS: 'Aadhaar or recent utility bill',
  INCOME: 'Salary slips or ITR',
}

const MAX_BYTES = 5 * 1024 * 1024

/** One document type: pick a file, upload it, show "✅ file name" once uploaded. */
export default function DocumentUploadRow({ appId, docType, label, uploaded, onUploaded }) {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const inputId = `file-${docType}`

  async function upload() {
    if (!file) return
    if (file.size > MAX_BYTES) {
      toast.error('File must be 5 MB or smaller')
      return
    }
    const form = new FormData()
    form.append('docType', docType)
    form.append('file', file)
    setBusy(true)
    try {
      const res = await client.post(`/applications/${appId}/documents`, form)
      toast.success(`${label} uploaded`)
      setFile(null)
      onUploaded?.(res.data)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="font-medium text-navy">{label}</p>
        <p className="text-xs text-slate-500">{DOC_HINTS[docType]}</p>
        {uploaded && (
          <p className="mt-1 flex items-center gap-1 truncate text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4 shrink-0" /> {uploaded.fileName}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <label
          htmlFor={inputId}
          className="max-w-44 cursor-pointer truncate rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-600 hover:border-teal hover:text-teal"
        >
          {file ? file.name : uploaded ? 'Replace file' : 'Choose file'}
        </label>
        <input
          id={inputId}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <Button variant="secondary" onClick={upload} disabled={!file} loading={busy}>
          {!busy && <Upload className="h-4 w-4" />} Upload
        </Button>
      </div>
    </div>
  )
}
