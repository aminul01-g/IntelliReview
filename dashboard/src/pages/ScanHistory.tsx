import React, { useState } from 'react'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useScanHistory, useScanReport, ScanMetadata } from '@/hooks/useScanHistory'
import * as Dialog from '@radix-ui/react-dialog'
import { X, FileCode } from 'lucide-react'

// --- DIALOG COMPONENT FOR MONGODB REPORTS ---
function ReportDialog({ scanId, onClose }: { scanId: string | null, onClose: () => void }) {
  const { data, isLoading } = useScanReport(scanId);

  return (
    <Dialog.Root open={!!scanId} onOpenChange={(open: boolean) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 grid w-full max-w-4xl translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 sm:rounded-lg md:w-full max-h-[85vh] flex flex-col">
          <div className="flex flex-col space-y-1.5">
            <Dialog.Title className="text-lg font-semibold leading-none tracking-tight">
               Historical Scan Report Details
            </Dialog.Title>
            <Dialog.Description className="text-sm text-muted-foreground">
               Pulling dense JSON diff analysis from MongoDB Archive for Scan ID: {scanId}
            </Dialog.Description>
          </div>
          
          <div className="flex-1 overflow-auto border border-border rounded-md bg-muted/10 p-4 relative min-h-[300px]">
             {isLoading ? (
               <div className="absolute inset-0 flex items-center justify-center flex-col gap-3 text-muted-foreground animate-pulse">
                  <FileCode className="h-8 w-8 opacity-40" />
                  <p className="text-sm">Retrieving payload from MongoDB...</p>
               </div>
             ) : data ? (
               <pre className="text-xs font-mono whitespace-pre-wrap text-muted-foreground">
                  {JSON.stringify(data, null, 2)}
               </pre>
             ) : (
               <div className="absolute inset-0 flex items-center justify-center">
                  <p className="text-sm text-muted-foreground">No historical report found or failed to load.</p>
               </div>
             )}
          </div>
          
          <Dialog.Close asChild>
            <button className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none">
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// --- TABLE CONFIGURATION ---
const columnHelper = createColumnHelper<ScanMetadata>()

export function ScanHistory() {
  const [page, setPage] = useState(1);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  
  const { data, isLoading } = useScanHistory(page, 10);

  const columns = [
    columnHelper.accessor('project_name', {
      header: 'Project',
      cell: (info: any) => <span className="font-medium">{info.getValue()}</span>,
    }),
    columnHelper.accessor('date', {
      header: 'Scan Date',
      cell: (info: any) => new Date(info.getValue()).toLocaleDateString(),
    }),
    columnHelper.accessor('health_score', {
      header: 'Health Score',
      cell: (info: any) => {
         const score = info.getValue()
         return (
           <div className="flex items-center gap-2">
              <div className="h-2 w-16 bg-muted rounded-full overflow-hidden">
                 <div 
                   className={`h-full ${score > 80 ? 'bg-green-500' : score > 50 ? 'bg-yellow-500' : 'bg-destructive'}`}
                   style={{ width: `${score}%` }}
                 />
              </div>
              <span className="text-xs font-mono">{score}/100</span>
           </div>
         )
      }
    }),
    columnHelper.accessor('technical_debt_hours', {
      header: 'Tech Debt',
      cell: (info: any) => <span className="text-muted-foreground">{info.getValue()} hrs</span>,
    }),
    columnHelper.accessor('critical_vulnerabilities', {
      header: 'Critical Findings',
      cell: (info: any) => (
        <span className={info.getValue() > 0 ? "text-destructive font-semibold" : "text-green-500"}>
          {info.getValue()}
        </span>
      )
    }),
    columnHelper.display({
      id: 'actions',
      cell: (props: any) => (
        <button 
           onClick={() => setSelectedScanId(props.row.original.id)}
           className="text-xs font-medium text-primary hover:underline hover:text-primary/80 transition-colors"
        >
           View Details / Diff (MongoDB)
        </button>
      )
    })
  ]

  const safeData = data?.data || [];

  const table = useReactTable({
    data: safeData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analysis History</h1>
        <p className="text-muted-foreground">View and filter past security scans aggregated from PostgreSQL metadata.</p>
      </div>

      <div className="border border-border rounded-lg bg-card overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 text-muted-foreground border-b border-border uppercase text-[10px] tracking-wider">
              {table.getHeaderGroups().map((headerGroup: any) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header: any) => (
                    <th key={header.id} className="px-4 py-3 font-semibold">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-border/60">
              {isLoading && !data ? (
                 <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground animate-pulse">Loading relational metadata via Axios/React Query...</td>
                 </tr>
              ) : safeData.length === 0 ? (
                 <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No scan history found.</td>
                 </tr>
              ) : table.getRowModel().rows.map((row: any) => (
                <tr key={row.id} className="hover:bg-muted/30 transition-colors">
                  {row.getVisibleCells().map((cell: any) => (
                    <td key={cell.id} className="px-4 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-border flex items-center justify-between text-sm bg-muted/10">
           <span className="text-muted-foreground font-medium">Showing page {page}</span>
           <div className="flex gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 border border-border rounded-md disabled:opacity-50 hover:bg-muted/50 transition-colors font-medium bg-background"
              >Previous</button>
              <button 
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1.5 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors font-medium"
              >Next</button>
           </div>
        </div>
      </div>
      
      <ReportDialog scanId={selectedScanId} onClose={() => setSelectedScanId(null)} />
    </div>
  )
}
