import * as vscode from 'vscode';
import axios from 'axios';

// Collection to hold the squiggly lines (diagnostics)
let diagnosticCollection: vscode.DiagnosticCollection;

// Output channel for the AI Review Markdown
let outputChannel: vscode.OutputChannel;

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

        const document = editor.document;
        await runAnalysis(document);
    });

    // Command: Clear Diagnostics
    let clearCmd = vscode.commands.registerCommand('intellireview.clearDiagnostics', () => {
        diagnosticCollection.clear();
        outputChannel.clear();
        vscode.window.showInformationMessage('IntelliReview results cleared.');
    });

    context.subscriptions.push(analyzeCmd, clearCmd);
}

async function runAnalysis(document: vscode.TextDocument) {
    const config = vscode.workspace.getConfiguration('intellireview');
    const serverUrl = config.get<string>('serverUrl', 'http://127.0.0.1:8000/api/v1');
    const apiToken = config.get<string>('apiToken', '');

    const code = document.getText();
    if (!code.trim()) {
        vscode.window.showInformationMessage('File is empty.');
        return;
    }

    // Map VS Code language IDs to IntelliReview expected IDs
    let langId = document.languageId;
    if (langId === 'javascriptreact' || langId === 'typescript' || langId === 'typescriptreact') langId = 'javascript';
    if (langId === 'cpp' || langId === 'c') langId = 'cpp';

    if (!apiToken) {
        vscode.window.showErrorMessage('IntelliReview API Token is missing. Please configure it in the extension settings.');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "IntelliReview: Analyzing code...",
        cancellable: false
    }, async (progress: any) => {
        try {
            // Call the local backend API
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
                // Line numbers are 1-indexed in our API, 0-indexed in VS Code
                const lineNum = Math.min(Math.max(0, (issue.line || 1) - 1), document.lineCount - 1);
                const lineRange = document.lineAt(lineNum).range;

                let severity = vscode.DiagnosticSeverity.Information;
                const sv = issue.severity?.toLowerCase();
                if (sv === 'critical' || sv === 'high') severity = vscode.DiagnosticSeverity.Error;
                else if (sv === 'medium') severity = vscode.DiagnosticSeverity.Warning;

                let message = `[${issue.type}] ${issue.message}`;
                if (issue.suggestion) {
                    message += `\nSuggestion: ${issue.suggestion}`;
                }

                const diagnostic = new vscode.Diagnostic(lineRange, message, severity);
                diagnostic.source = 'IntelliReview';
                diagnostic.code = issue.type;
                
                diagnostics.push(diagnostic);
            }

            diagnosticCollection.set(document.uri, diagnostics);

            // 2. Output AI General Review to Channel
            if (data.ai_general_review) {
                outputChannel.clear();
                outputChannel.appendLine('=== IntelliReview AI Architecture Report ===\n');
                outputChannel.appendLine(data.ai_general_review);
                outputChannel.show(true); // Bring out channel to front
            }

            vscode.window.showInformationMessage(`IntelliReview found ${issues.length} issues.`);

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || error.message;
            vscode.window.showErrorMessage(`IntelliReview Analysis Failed: ${msg}`);
        }
    });
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
}
