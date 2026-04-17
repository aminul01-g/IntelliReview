import * as vscode from 'vscode';
import axios from 'axios';
import { spawn } from 'child_process';

// Collection to hold the squiggly lines (diagnostics)
let diagnosticCollection: vscode.DiagnosticCollection;

// Output channel for the AI Review Markdown
let outputChannel: vscode.OutputChannel;

// Store the latest findings map for Quick Fixes
// Key: Document URI string + ":" + Line Number + ":" + Diagnostic Code
interface QuickFixData {
    suggestion: string;
    description: string;
}
const quickFixRegistry = new Map<string, QuickFixData>();

export function activate(context: vscode.ExtensionContext) {
    console.log('IntelliReview VS Code Extension is now active!');

    // Initialize UI components
    diagnosticCollection = vscode.languages.createDiagnosticCollection('intellireview');
    outputChannel = vscode.window.createOutputChannel('IntelliReview AI');

    context.subscriptions.push(diagnosticCollection);
    context.subscriptions.push(outputChannel);

    // Command: Analyze Current File
    let analyzeCmd = vscode.commands.registerCommand('intellireview.analyzeCurrentFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active file to analyze.');
            return;
        }
        await runAnalysis(editor.document, false);
    });

    // Command: Clear Diagnostics
    let clearCmd = vscode.commands.registerCommand('intellireview.clearDiagnostics', () => {
        diagnosticCollection.clear();
        outputChannel.clear();
        quickFixRegistry.clear();
        vscode.window.showInformationMessage('IntelliReview results cleared.');
    });

    // Auto-analysis on save (Shift-Left)
    let saveSub = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('intellireview');
        if (config.get<boolean>('analyzeOnSave', true)) {
            await runAnalysis(document, true);
        }
    });

    // Register Tab-to-Fix Code Action Provider
    let codeActionProvider = vscode.languages.registerCodeActionsProvider(
        { scheme: 'file' },
        new IntelliReviewFixProvider(),
        { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    );

    context.subscriptions.push(analyzeCmd, clearCmd, saveSub, codeActionProvider);
}

async function runAnalysis(document: vscode.TextDocument, isSilent: boolean) {
    const config = vscode.workspace.getConfiguration('intellireview');
    const serverUrl = config.get<string>('serverUrl', 'http://127.0.0.1:8000/api/v1');
    const apiToken = config.get<string>('apiToken', '');
    const enableMcp = config.get<boolean>('enableMcpMode', false);

    const code = document.getText();
    if (!code.trim()) {
        if (!isSilent) vscode.window.showInformationMessage('File is empty.');
        return;
    }

    let langId = document.languageId;
    if (langId === 'javascriptreact' || langId === 'typescript' || langId === 'typescriptreact') langId = 'javascript';
    if (langId === 'cpp' || langId === 'c') langId = 'cpp';

    if (!apiToken && !enableMcp) {
        if (!isSilent) vscode.window.showErrorMessage('IntelliReview API Token is missing. Please configure it.');
        return;
    }

    // Clean previous quick fixes for this document
    const docUriStr = document.uri.toString();
    for (const key of quickFixRegistry.keys()) {
        if (key.startsWith(docUriStr)) {
            quickFixRegistry.delete(key);
        }
    }

    const task = async () => {
        try {
            // Future MCP stdout/stdin framework hook goes here.
            // Using HTTP for structural JSON diagnostics.
            const response = await axios.post(`${serverUrl}/analysis/analyze`, {
                code: code,
                language: langId,
                file_path: document.fileName
            }, {
                headers: { "Authorization": `Bearer ${apiToken}` }
            });

            const data = response.data;
            const issues = data.issues || [];

            // 1. Update Diagnostics (Squigglies)
            const diagnostics: vscode.Diagnostic[] = [];
            
            for (const issue of issues) {
                const lineNum = Math.min(Math.max(0, (issue.line || 1) - 1), document.lineCount - 1);
                const lineRange = document.lineAt(lineNum).range;

                let severity = vscode.DiagnosticSeverity.Information; // 🟣 Preexisting
                const sv = issue.severity?.toLowerCase();
                if (sv === 'critical' || sv === 'high' || sv === 'important') severity = vscode.DiagnosticSeverity.Error; // 🔴
                else if (sv === 'medium' || sv === 'nit') severity = vscode.DiagnosticSeverity.Warning; // 🟡

                // Severity Marker Prefix Map
                const markerMap: Record<number, string> = {
                    [vscode.DiagnosticSeverity.Error]: '🔴 [Important]',
                    [vscode.DiagnosticSeverity.Warning]: '🟡 [Nit]',
                    [vscode.DiagnosticSeverity.Information]: '🟣 [Preexisting]'
                };
                
                const prefix = markerMap[severity];
                let message = `${prefix} ${issue.message}`;

                const diagnostic = new vscode.Diagnostic(lineRange, message, severity);
                diagnostic.source = 'IntelliReview';
                diagnostic.code = issue.type;
                
                diagnostics.push(diagnostic);

                // Register Quick Fix Data if suggestion exists
                if (issue.suggestion) {
                    const key = `${docUriStr}:${lineNum}:${issue.type}`;
                    quickFixRegistry.set(key, {
                        suggestion: issue.suggestion,
                        description: `IntelliReview: Auto-fix ${issue.type}`
                    });
                }
            }

            diagnosticCollection.set(document.uri, diagnostics);

            // 2. Output AI General Review to Channel
            if (data.ai_general_review && !isSilent) {
                outputChannel.clear();
                outputChannel.appendLine('=== IntelliReview AI Architecture Report ===\n');
                outputChannel.appendLine(data.ai_general_review);
                outputChannel.show(true); 
            }

            if (!isSilent) vscode.window.showInformationMessage(`IntelliReview found ${issues.length} issues.`);

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || error.message;
            if (!isSilent) vscode.window.showErrorMessage(`IntelliReview Analysis Failed: ${msg}`);
        }
    };

    if (isSilent) {
        await task();
    } else {
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "IntelliReview: Analyzing code...",
            cancellable: false
        }, async () => task());
    }
}

// Quick Fix Provider (Tab-to-fix)
class IntelliReviewFixProvider implements vscode.CodeActionProvider {
    provideCodeActions(document: vscode.TextDocument, range: vscode.Range | vscode.Selection, context: vscode.CodeActionContext): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];
        
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source === 'IntelliReview') {
                const key = `${document.uri.toString()}:${diagnostic.range.start.line}:${diagnostic.code}`;
                const fixData = quickFixRegistry.get(key);
                
                if (fixData) {
                    const action = new vscode.CodeAction(fixData.description, vscode.CodeActionKind.QuickFix);
                    action.edit = new vscode.WorkspaceEdit();
                    
                    // Add the suggested text below the error line as an auto-fix 
                    // (Real autofix applies exact diff, this replaces line or appends suggestion)
                    // We append it nicely formatted
                    const lineText = document.lineAt(diagnostic.range.start.line).text;
                    const whitespaceMatch = lineText.match(/^\s*/);
                    const indentation = whitespaceMatch ? whitespaceMatch[0] : '';
                    
                    action.edit.replace(
                        document.uri, 
                        document.lineAt(diagnostic.range.start.line).range, 
                        `${indentation}${fixData.suggestion} // Auto-fixed by IntelliReview`
                    );
                    
                    action.diagnostics = [diagnostic];
                    action.isPreferred = true; // Allows "Tab to fix" behavior conceptually
                    actions.push(action);
                }
            }
        }
        
        return actions;
    }
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    quickFixRegistry.clear();
}

