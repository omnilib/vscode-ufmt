# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
Runner to use when running under a different interpreter.
"""

import os
import pathlib
import sys
import traceback


# **********************************************************
# Update sys.path before importing any bundled libraries.
# **********************************************************
def update_sys_path(path_to_add: str, strategy: str) -> None:
    """Add given path to `sys.path`."""
    if path_to_add not in sys.path and os.path.isdir(path_to_add):
        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        elif strategy == "fromEnvironment":
            sys.path.append(path_to_add)


# Ensure that we can import LSP libraries, and other bundled libraries.
update_sys_path(
    os.fspath(pathlib.Path(__file__).parent.parent / "libs"),
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)


# pylint: disable=wrong-import-position,import-error
from . import jsonrpc, utils

RPC = jsonrpc.create_json_rpc(sys.stdin.buffer, sys.stdout.buffer)

EXIT_NOW = False
while not EXIT_NOW:
    msg = RPC.receive_data()

    method = msg["method"]
    if method == "exit":
        EXIT_NOW = True
        continue

    if method == "run":
        is_exception = False
        # This is needed to preserve sys.path, pylint modifies
        # sys.path and that might not work for this scenario
        # next time around.
        with utils.substitute_attr(sys, "path", sys.path[:]):
            try:
                import ufmt
                import ufmt.util

                if ufmt.__version__.startswith("1."):
                    raise RuntimeError("Requires ufmt >= 2.0.0b1")

                document_path = pathlib.Path(msg["document_path"]).resolve()
                source_bytes = msg["source"].encode("utf-8")
                black_config = ufmt.util.make_black_config(document_path)
                usort_config = ufmt.types.UsortConfig.find(document_path)
                ufmt_result = ufmt.ufmt_bytes(document_path, source_bytes, encoding="utf-8", black_config=black_config, usort_config=usort_config,)
                result = utils.RunResult(ufmt_result.decode("utf-8"), "")
            except Exception:  # pylint: disable=broad-except
                result = utils.RunResult("", traceback.format_exc(chain=True))
                is_exception = True

        response = {"id": msg["id"]}
        if result.stderr:
            response["error"] = result.stderr
            response["exception"] = is_exception
        elif result.stdout:
            response["result"] = result.stdout

        RPC.send_data(response)
