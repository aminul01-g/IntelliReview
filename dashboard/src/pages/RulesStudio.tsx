import React, { useState } from 'react'
import Editor from '@monaco-editor/react'
import * as Lucide from 'lucide-react'
import { api } from '@/lib/api'
import { useMutation } from '@tanstack/react-query'

const { Play } = Lucide as any

const DEFAULT_RULE = `rules:
  - id: custom-sql-injection
    message: "Direct SQL execution"
    severity: ERROR
    language: python
    pattern: |
      $DB.execute($QUERY)
`

export function RulesStudio() {
  const [ruleCode, setRuleCode] = useState(DEFAULT_RULE)
  const [testCode, setTestCode] = useState('db.execute("SELECT * FROM users")')

  const testMutation = useMutation({
    mutationFn: async () => {
      try {
        // Use the correct backend endpoint for custom rule evaluation
        const { data } = await api.post('/analysis/custom-rules', {
          code: testCode,
          language: 'python',
          filename: 'test.py',
          rules_yaml: ruleCode  // Send the YAML directly
        });

        // Backend returns synchronous result with issues
        return data;
      } catch (error: any) {
        console.error('Custom rule evaluation error:', error);
        throw error;
      }
    },
    onError: (error: any) => {
      console.error('Mutation error:', error);
    }
  });

  const handleRunTest = () => {
    testMutation.mutate();
  };

  // Determine what to show
  const isPending = testMutation.isPending;
  const hasError = testMutation.isError;
  const errorMessage = testMutation.error instanceof Error ? testMutation.error.message : 'Unknown error';

  // Get results from mutation data
  const matchResult = testMutation.data;

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between shrink-0">
         <div>
            <h1 className="text-2xl font-bold tracking-tight">Custom Rules Studio</h1>
            <p className="text-muted-foreground">Define and test custom IntelliReview rules via Monaco structural matching endpoints.</p>
         </div>
         <button 
            onClick={handleRunTest}
            disabled={isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm flex items-center gap-2 transition-colors disabled:opacity-50 shadow-sm"
         >
            <Play className="h-4 w-4 fill-current" /> Run Rule Evaluation
         </button>
      </div>

      {hasError && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 flex items-start gap-3">
          <div className="flex-1">
            <p className="text-sm font-medium text-destructive">Error running rule evaluation:</p>
            <p className="text-sm text-destructive/80 mt-1">{errorMessage}</p>
          </div>
        </div>
      )}
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
         <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-card min-h-0 shadow-sm">
            <div className="bg-muted px-4 py-2 text-sm font-medium border-b border-border flex justify-between tracking-wide text-muted-foreground">
               Rule Definition (.intellireview.yml)
            </div>
            <div className="flex-1 relative bg-[#1e1e1e]">
                <Editor
                  height="100%"
                  defaultLanguage="yaml"
                  theme="vs-dark"
                  value={ruleCode}
                  onChange={(val: string | undefined) => setRuleCode(val || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: 'ui-monospace, Consolas, monospace',
                    padding: { top: 16 }
                  }}
                />
            </div>
         </div>
         
         <div className="flex flex-col gap-6 min-h-0">
             <div className="flex-1 flex flex-col border border-border rounded-lg overflow-hidden bg-card min-h-[50%] shadow-sm">
                <div className="bg-muted px-4 py-2 text-sm font-medium border-b border-border text-muted-foreground">
                   Test Snippet (Python)
                </div>
                <div className="flex-1 relative bg-[#1e1e1e]">
                    <Editor
                      height="100%"
                      defaultLanguage="python"
                      theme="vs-dark"
                      value={testCode}
                      onChange={(val: string | undefined) => setTestCode(val || '')}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        padding: { top: 16 }
                      }}
                    />
                </div>
             </div>
             
             <div className="flex-1 border border-border rounded-lg bg-card p-4 overflow-auto min-h-[30%] shadow-sm">
                <div className="text-sm font-medium border-b border-border pb-2 mb-4 text-muted-foreground tracking-wide">Structural Evaluation Results via Backend</div>
                {isPending ? (
                   <div className="animate-pulse flex flex-col gap-3">
                      <div className="h-4 w-1/3 bg-muted rounded"></div>
                      <div className="h-4 w-1/2 bg-muted rounded"></div>
                   </div>
                ) : matchResult ? (
                   <div className="space-y-4">
                     <div className="text-sm font-medium flex items-center gap-2">
                       Issues Found: <span className="font-bold text-destructive bg-destructive/10 px-2 py-0.5 rounded-full">{matchResult.issues_found || matchResult.issues?.length || 0}</span>
                     </div>
                     <pre className="text-xs bg-muted/40 border border-border rounded-md p-3 text-muted-foreground font-mono whitespace-pre-wrap">
                        {JSON.stringify(matchResult, null, 2)}
                     </pre>
                   </div>
                ) : (
                   <div className="text-sm text-muted-foreground flex h-32 items-center justify-center opacity-50 border-2 border-dashed border-border rounded-md">
                     Hit "Run Rule Evaluation" to pipe Editor states to FastAPI
                   </div>
                )}
             </div>
         </div>
      </div>
    </div>
  )
}
