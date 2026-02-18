import { useState, useCallback } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [inputFile, setInputFile] = useState<File | null>(null)
  const [outputUrl, setOutputUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const processPdf = useCallback(async () => {
    if (!inputFile) return
    setLoading(true)
    setError(null)
    setOutputUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })

    try {
      const formData = new FormData()
      formData.append('file', inputFile)
      const res = await fetch(`${API_URL || ''}/api/process`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const detail = data.detail
        const msg = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg).join(', ')
            : `Request failed: ${res.status}`
        throw new Error(msg)
      }
      const blob = await res.blob()
      setOutputUrl(URL.createObjectURL(blob))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Processing failed')
    } finally {
      setLoading(false)
    }
  }, [inputFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file?.type === 'application/pdf') {
      setInputFile(file)
      setError(null)
    } else {
      setError('Please drop a PDF file')
    }
  }, [])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setInputFile(file)
      setError(null)
    }
  }, [])

  return (
    <div className="app">
      <header className="header">
        <h1>Searchable PDF</h1>
        <p>Upload a scanned PDF to add a searchable text layer</p>
      </header>

      <div className="panels">
        <section className="panel panel-left">
          <h2>Input PDF</h2>
          <div
            className={`dropzone ${inputFile ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              id="file-input"
              className="file-input"
            />
            {inputFile ? (
              <div className="file-info">
                <span className="filename">{inputFile.name}</span>
                <span className="filesize">
                  {(inputFile.size / 1024).toFixed(1)} KB
                </span>
              </div>
            ) : (
              <label htmlFor="file-input" className="dropzone-label">
                Drop PDF here or click to browse
              </label>
            )}
          </div>
          <button
            className="btn-process"
            onClick={processPdf}
            disabled={!inputFile || loading}
          >
            {loading ? 'Processing…' : 'Process PDF'}
          </button>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="panel panel-right">
          <h2>Output PDF</h2>
          <div className="viewer-area">
            {outputUrl ? (
              <>
                <div className="search-hint">
                  Use Ctrl+F (Cmd+F on Mac) to search within the PDF
                </div>
                <iframe
                  src={`${outputUrl}#toolbar=1`}
                  title="Output PDF"
                  className="pdf-viewer"
                />
                <a
                  href={outputUrl}
                  download="searchable_output.pdf"
                  className="btn-download"
                >
                  Download PDF
                </a>
              </>
            ) : (
              <div className="placeholder">
                {loading
                  ? 'Converting…'
                  : 'Process a PDF to view the searchable output here'}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
