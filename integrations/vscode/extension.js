const vscode = require('vscode');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('IntelliReview extension is active');

    let disposable = vscode.commands.registerCommand('intellireview.analyze', async function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }

        const document = editor.document;
        const code = document.getText();
        const language = document.languageId;

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "IntelliReview analyzing code...",
            cancellable: false
        }, async (progress) => {
            try {
                // In a real extension, we would use axios/node-fetch to call the API
                // and show diagnostics in the editor
                vscode.window.showInformationMessage(`Analyzed ${document.fileName} successfully!`);
            } catch (error) {
                vscode.window.showErrorMessage(`Analysis failed: ${error.message}`);
            }
        });
    });

    context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
}
