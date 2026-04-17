import React, { useState, useRef } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'

export function UploadProject() {
  const [isDragging, setIsDragging] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [pollMessage, setPollMessage] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: any) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: any) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: any) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setIsUploading(true)
    setUploadStatus('idle')
    setPollMessage('Uploading files to server...')
    
    try {
      const formData = new FormData()
      files.forEach(file => {
        // FastAPI reads the original relative path structure automatically if available
        formData.append('files', file)
      })

      const response = await api.post('/analysis/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      const taskId = response.data.task_id
      setPollMessage('Upload complete. Task queued in Celery...')
      
      const pollInterval = window.setInterval(async () => {
        try {
          const statusRes = await api.get(`/analysis/upload/status/${taskId}`)
          const state = statusRes.data.status
          setPollMessage(statusRes.data.info || `Processing: ${state}`)
          
          if (state === 'SUCCESS') {
            window.clearInterval(pollInterval)
            setIsUploading(false)
            setUploadStatus('success')
            setPollMessage('Scan Complete!')
          } else if (state === 'FAILURE' || state === 'REVOKED') {
            window.clearInterval(pollInterval)
            setIsUploading(false)
            setUploadStatus('error')
            setPollMessage(statusRes.data.error || 'Task encountered a failure.')
          }
        } catch (pollErr) {
            window.clearInterval(pollInterval)
            setIsUploading(false)
            setUploadStatus('error')
            setPollMessage('Error polling status from server.')
        }
      }, 2000)

    } catch (err: any) {
      setIsUploading(false)
      setUploadStatus('error')
      setPollMessage(err.response?.data?.detail || err.message || 'Upload failed')
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 flex flex-col h-full max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Project Upload</h1>
        <p className="text-muted-foreground text-lg mt-1">Upload a directory or multiple logic files to run a comprehensive multi-agent architectural scan.</p>
      </div>

      <div 
        className={`flex-1 border-2 border-dashed rounded-xl p-12 transition-all duration-300 flex items-center justify-center relative overflow-hidden bg-muted/5 ${
          isDragging ? 'border-primary bg-primary/5' : 'border-border/60 hover:border-border hover:bg-muted/10'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 via-transparent to-purple-500/5 opacity-50 pointer-events-none" />

        <div className="flex flex-col items-center justify-center text-center space-y-6 relative z-10">
          <div className={`h-24 w-24 rounded-full flex items-center justify-center transition-all duration-500 ${isDragging ? 'bg-primary/20 scale-110' : 'bg-muted'}`}>
            <Upload className={`h-12 w-12 transition-colors duration-500 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
          </div>
          
          <div className="space-y-2">
            <h3 className="text-xl font-semibold tracking-tight">
              {isDragging ? 'Drop to queue files' : 'Drag & drop directory here'}
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              You can also select a folder structurally to preserve relative file paths for dependency tracking.
            </p>
          </div>

          <button 
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-10 px-6 py-2 shadow-sm"
          >
            Browse Files
          </button>
          
          <input 
            type="file" 
            className="hidden" 
            ref={fileInputRef as any} 
            onChange={handleFileInput} 
            multiple 
            {...({ webkitdirectory: "true" } as any)} 
          />
        </div>
      </div>

      {files.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-4">
           <div className="flex items-center justify-between">
             <div className="flex items-center gap-2 font-medium">
               <FileText className="h-5 w-5 text-primary" />
               <span>Ready for Analysis ({files.length} items)</span>
             </div>
             {uploadStatus === 'success' ? (
                <div className="px-3 py-1 bg-green-500/10 text-green-500 text-xs font-semibold rounded-full flex items-center gap-1">
                  <CheckCircle className="h-3.5 w-3.5" /> Scan Queued
                </div>
             ) : uploadStatus === 'error' ? (
                <div className="px-3 py-1 bg-destructive/10 text-destructive text-xs font-semibold rounded-full flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5" /> Scan Failed
                </div>
             ) : null}
           </div>
           
           {(isUploading || uploadStatus !== 'idle') && pollMessage && (
             <div className="text-sm font-medium text-muted-foreground bg-muted/30 py-2 px-3 rounded-md flex items-center gap-2">
               {isUploading && <RefreshCw className="h-4 w-4 animate-spin text-primary" />}
               <span>{pollMessage}</span>
             </div>
           )}
           
           <div className="h-32 overflow-y-auto border border-border rounded-md bg-muted/20 p-2 custom-scrollbar">
             {files.slice(0, 100).map((file, idx) => (
               <div key={idx} className="text-xs text-muted-foreground font-mono truncate px-2 py-1 hover:bg-muted/50 rounded transition-colors">
                  {file.webkitRelativePath || file.name}
               </div>
             ))}
             {files.length > 100 && (
               <div className="text-xs text-muted-foreground font-mono px-2 py-1 italic opacity-70">
                 ... and {files.length - 100} more files
               </div>
             )}
           </div>

           <div className="flex justify-end gap-3 pt-2">
             <button 
               onClick={() => { setFiles([]); setUploadStatus('idle'); setPollMessage(''); }}
               disabled={isUploading}
               className="h-10 px-4 py-2 text-sm font-medium border border-border rounded-md text-foreground bg-transparent hover:bg-muted/50 transition-colors disabled:opacity-50"
             >
               Clear Queue
             </button>
             <button 
               onClick={handleUpload}
               disabled={isUploading || uploadStatus === 'success'}
               className="h-10 px-6 py-2 text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
             >
               {isUploading ? (
                 <>
                   <RefreshCw className="h-4 w-4 animate-spin" />
                   Processing...
                 </>
               ) : uploadStatus === 'success' ? (
                 'Redirecting to History...'
               ) : (
                 'Start Deep Scan'
               )}
             </button>
           </div>
        </div>
      )}
    </div>
  )
}

