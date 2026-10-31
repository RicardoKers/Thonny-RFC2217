"""Exercise actual completion, hover and diagnostics in a packaged runtime.

Run with that runtime's python.exe -I, not the development virtual environment.
No board, GUI session, npm or separate Node installation is required.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import List, Union


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output-json", "--outputjson", dest="output", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if Path(sys.prefix).resolve() != runtime:
        raise SystemExit("Use the selected runtime's python.exe -I to run this probe.")

    import thonny
    from thonny import lsp_types
    from thonny.plugins.basedpyright import BasedpyrightProxy

    assert Path(thonny.__file__).resolve().is_relative_to(runtime)
    os.environ["PATH"] = str(runtime / "Scripts") + os.pathsep + os.environ.get("PATH", "")
    result = {"status": "FAIL", "private_runtime": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="thonny-rfc2217-lsp-") as directory:
        workspace = Path(directory).resolve()
        stubs = workspace / "stubs"
        stubs.mkdir()
        thonny._thonny_user_dir = str(workspace)
        workbench = SimpleNamespace(
            event_generate=lambda *values: None,
            in_debug_mode=lambda: False,
            after=lambda *values: None,
            report_exception=lambda: (_ for _ in ()).throw(
                RuntimeError("Language-server message processing failed")
            ),
            get_local_project_path=lambda: None,
        )
        backend = SimpleNamespace(
            interpreter_is_cpython_compatible=lambda: True,
            has_local_interpreter=lambda: True,
            get_target_executable=lambda: sys.executable,
            get_user_stubs_location=lambda: str(stubs),
        )
        thonny._workbench = workbench
        thonny._runner = SimpleNamespace(get_backend_proxy=lambda: backend)

        class ProbeProxy(BasedpyrightProxy):
            def get_settings(self):
                settings = super().get_settings()
                settings["basedpyright"]["analysis"]["typeCheckingMode"] = "basic"
                return settings

        source = workspace / "feature_check.py"
        source.write_text(
            'import math\nvalue: int = "wrong"\nroot = math.sqrt(9)\n', encoding="utf-8"
        )
        proxy = ProbeProxy(
            lsp_types.InitializeParams(
                processId=os.getpid(),
                capabilities=lsp_types.ClientCapabilities(
                    textDocument=lsp_types.TextDocumentClientCapabilities(
                        publishDiagnostics=lsp_types.PublishDiagnosticsClientCapabilities(
                            relatedInformation=False
                        )
                    )
                ),
                rootUri=workspace.as_uri(),
                workspaceFolders=[
                    lsp_types.WorkspaceFolder(uri=workspace.as_uri(), name="feature-check")
                ],
            )
        )

        def wait_for(predicate, description, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                proxy._process_messages_from_server()
                if predicate():
                    return
                if proxy._proc.poll() is not None:
                    raise RuntimeError("Language server exited while waiting for " + description)
                time.sleep(0.02)
            raise TimeoutError("No language-server result for " + description)

        try:
            wait_for(proxy.is_initialized, "initialization")
            assert Path(proxy._proc.args[0]).name.lower() == "node.exe", proxy._proc.args
            proxy.notify_did_open_text_document(
                lsp_types.DidOpenTextDocumentParams(
                    textDocument=lsp_types.TextDocumentItem(
                        uri=source.as_uri(),
                        languageId="python",
                        version=1,
                        text=source.read_text(encoding="utf-8"),
                    )
                )
            )
            document = lsp_types.TextDocumentIdentifier(uri=source.as_uri())
            completions = []
            hovers = []

            def on_completion(
                response: lsp_types.LspResponse[
                    Union[List[lsp_types.CompletionItem], lsp_types.CompletionList, None]
                ],
            ):
                completions.append(response.get_result_or_raise())

            def on_hover(response: lsp_types.LspResponse[Union[lsp_types.Hover, None]]):
                hovers.append(response.get_result_or_raise())

            proxy.request_completion(
                lsp_types.CompletionParams(
                    textDocument=document, position=lsp_types.Position(line=2, character=12)
                ),
                on_completion,
            )
            proxy.request_hover(
                lsp_types.HoverParams(
                    textDocument=document, position=lsp_types.Position(line=2, character=14)
                ),
                on_hover,
            )
            wait_for(lambda: bool(completions), "math completion")
            wait_for(lambda: bool(hovers), "sqrt hover")
            completion = completions[0]
            items = (
                completion.items if isinstance(completion, lsp_types.CompletionList) else completion
            )
            assert items, "Completion list is empty"
            labels = {item.label for item in items}
            assert "sqrt" in labels, sorted(labels)
            assert hovers[0] is not None and "sqrt" in str(hovers[0].contents), hovers[0]

            def assignment_error():
                # Only this one document is opened; accept the server's canonical
                # URI spelling, which can differ in Windows drive escaping/case.
                return any(
                    diagnostic.code == "reportAssignmentType" and diagnostic.range.start.line == 1
                    for diagnostics in proxy._diagnostics.values()
                    for diagnostic in diagnostics.diagnostics
                )

            wait_for(assignment_error, "intentional incompatible assignment diagnostic")
            result.update(
                status="PASS",
                server_name=proxy.server_info.name,
                server_version=proxy.server_info.version,
                completion_count=len(labels),
                completion_includes_sqrt=True,
                hover_includes_sqrt=True,
                assignment_type_diagnostic=True,
            )
        except Exception as error:
            result["error"] = str(error)
            result["diagnostics_seen"] = [
                {"code": item.code, "line": item.range.start.line, "message": item.message}
                for diagnostics in proxy._diagnostics.values()
                for item in diagnostics.diagnostics
            ]
            raise
        finally:
            proxy.shut_down()
            result["exit_code"] = proxy._proc.returncode
            result["server_stopped"] = proxy._proc.poll() is not None
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        assert proxy._proc.returncode == 0, proxy._proc.returncode

    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
