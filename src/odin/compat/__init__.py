"""Compatibility patches for third-party packages.

This module patches compatibility issues with third-party packages that have
broken imports or API changes. It should be imported early before any other
imports that might trigger the problematic imports.
"""


def patch_langchain_for_paddlex() -> None:
    """Patch langchain to provide compatibility shims for paddlex.

    paddlex (used by paddleocr 3.x) expects old langchain API paths:
    - langchain.docstore.document.Document -> langchain_core.documents.Document
    - langchain.text_splitter.RecursiveCharacterTextSplitter -> langchain_text_splitters

    This function creates the missing modules dynamically at runtime.
    """
    import sys
    import types

    # Check if langchain is installed
    try:
        import langchain
    except ImportError:
        return  # langchain not installed, nothing to patch

    # Check if langchain_core is available (modern langchain)
    try:
        from langchain_core.documents import Document
    except ImportError:
        return  # Old langchain, no patch needed

    # Create langchain.docstore module if it doesn't exist
    if "langchain.docstore" not in sys.modules:
        docstore = types.ModuleType("langchain.docstore")
        docstore.__path__ = []
        sys.modules["langchain.docstore"] = docstore
        langchain.docstore = docstore  # type: ignore

    # Create langchain.docstore.document module
    if "langchain.docstore.document" not in sys.modules:
        from langchain_core.documents import Document

        document_module = types.ModuleType("langchain.docstore.document")
        document_module.Document = Document  # type: ignore
        sys.modules["langchain.docstore.document"] = document_module

    # Create langchain.text_splitter module if it doesn't exist
    if "langchain.text_splitter" not in sys.modules:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            text_splitter = types.ModuleType("langchain.text_splitter")
            text_splitter.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter  # type: ignore
            sys.modules["langchain.text_splitter"] = text_splitter
            langchain.text_splitter = text_splitter  # type: ignore
        except ImportError:
            pass  # langchain_text_splitters not installed


def apply_all_patches() -> None:
    """Apply all compatibility patches."""
    patch_langchain_for_paddlex()
