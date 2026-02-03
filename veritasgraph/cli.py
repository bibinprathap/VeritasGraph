"""
VeritasGraph Command Line Interface
===================================

Entry point for the `veritasgraph` and `vg` commands.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from veritasgraph import __version__


def create_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="veritasgraph",
        description="VeritasGraph - Enterprise-Grade Graph RAG Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  veritasgraph --version          Show version
  veritasgraph info               Show system information
  veritasgraph ingest doc.pdf     Ingest a PDF document
  veritasgraph query "question"   Query the knowledge graph
  veritasgraph serve              Start the API server

For more information, visit: https://github.com/bibinprathap/VeritasGraph
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run VeritasGraph demo in different modes")
    demo_parser.add_argument(
        "--mode",
        type=str,
        choices=["lite", "local"],
        default="lite",
        help="Demo mode: 'lite' (cloud APIs, zero setup) or 'local' (offline with Ollama)"
    )
    demo_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use in local mode (e.g., llama3.2)"
    )

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the complete GraphRAG pipeline")
    start_parser.add_argument(
        "--mode",
        type=str,
        choices=["full"],
        default="full",
        help="Start mode: 'full' (complete GraphRAG pipeline)"
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show system information")
    info_parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if all dependencies are installed",
    )

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents into knowledge graph")
    ingest_parser.add_argument(
        "source",
        type=str,
        help="Path to PDF file, directory, or URL to ingest",
    )
    ingest_parser.add_argument(
        "--output-dir",
        type=str,
        default="./veritasgraph_output",
        help="Output directory for processed data",
    )
    ingest_parser.add_argument(
        "--vision-model",
        type=str,
        default="llama3.2-vision:11b",
        help="Vision model to use for document analysis",
    )
    ingest_parser.add_argument(
        "--ingest-mode",
        type=str,
        choices=["chunk", "document-centric", "page", "section", "auto"],
        default="document-centric",
        help="Ingestion strategy: 'chunk' (traditional 500-token chunks), "
             "'document-centric' (whole pages/sections as nodes - recommended), "
             "'page' (each page is one node), 'section' (each section is one node), "
             "'auto' (automatically choose based on document). Default: document-centric",
    )

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the knowledge graph")
    query_parser.add_argument(
        "question",
        type=str,
        help="Question to ask",
    )
    query_parser.add_argument(
        "--data-dir",
        type=str,
        default="./veritasgraph_output",
        help="Directory containing the knowledge graph data",
    )
    query_parser.add_argument(
        "--method",
        type=str,
        choices=["local", "global", "hybrid"],
        default="hybrid",
        help="Query method to use",
    )

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new VeritasGraph project")
    init_parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Path to initialize project in",
    )

    return parser


def cmd_info(args: argparse.Namespace) -> int:
    """Show system information."""
    print(f"VeritasGraph v{__version__}")
    print("=" * 40)
    print()
    
    print("Python Environment:")
    print(f"  Python: {sys.version}")
    print(f"  Platform: {sys.platform}")
    print()
    
    print("Core Dependencies:")
    deps = [
        ("ollama", "ollama"),
        ("PIL", "pillow"),
        ("pdf2image", "pdf2image"),
        ("networkx", "networkx"),
        ("numpy", "numpy"),
        ("matplotlib", "matplotlib"),
    ]
    
    for import_name, package_name in deps:
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "installed")
            print(f"  ✅ {package_name}: {version}")
        except ImportError:
            print(f"  ❌ {package_name}: not installed")
    
    print()
    print("Optional Dependencies:")
    optional_deps = [
        ("graphrag", "graphrag"),
        ("gradio", "gradio"),
        ("pyvis", "pyvis"),
        ("pandas", "pandas"),
        ("tiktoken", "tiktoken"),
    ]
    
    for import_name, package_name in optional_deps:
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "installed")
            print(f"  ✅ {package_name}: {version}")
        except ImportError:
            print(f"  ⚪ {package_name}: not installed (optional)")
    
    if args.check_deps:
        print()
        print("Checking Ollama connection...")
        try:
            import ollama
            client = ollama.Client()
            models = client.list()
            print("  ✅ Ollama is running")
            if hasattr(models, 'models'):
                model_names = [m.model for m in models.models]
            else:
                model_names = [m.get('name', '') for m in models.get('models', [])]
            print(f"  Available models: {', '.join(model_names[:5])}")
            if len(model_names) > 5:
                print(f"    ... and {len(model_names) - 5} more")
        except Exception as e:
            print(f"  ❌ Ollama not running or not accessible: {e}")
    
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest documents into knowledge graph."""
    from veritasgraph import VisionRAGConfig, VisionRAGPipeline
    
    source = Path(args.source)
    if not source.exists():
        print(f"❌ Source not found: {source}")
        return 1
    
    print(f"📄 Ingesting: {source}")
    
    # "Don't Chunk. Graph." - Document-centric mode treats whole pages/sections as nodes
    config = VisionRAGConfig(
        vision_model=args.vision_model,
        output_dir=args.output_dir,
        ingest_mode=args.ingest_mode,
    )
    
    pipeline = VisionRAGPipeline(config)
    
    if source.is_file() and source.suffix.lower() == ".pdf":
        doc = pipeline.ingest_pdf(str(source))
        if doc:
            print(f"✅ Successfully ingested: {doc.title}")
            print(f"   Pages: {len(doc.pages)}")
            print(f"   Output: {args.output_dir}")
        else:
            print("❌ Failed to ingest document")
            return 1
    elif source.is_dir():
        pdfs = list(source.glob("**/*.pdf"))
        print(f"Found {len(pdfs)} PDF files")
        for pdf in pdfs:
            doc = pipeline.ingest_pdf(str(pdf))
            if doc:
                print(f"  ✅ {pdf.name}")
            else:
                print(f"  ❌ {pdf.name}")
    else:
        print(f"❌ Unsupported source type: {source}")
        return 1
    
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Query the knowledge graph."""
    print(f"🔍 Query: {args.question}")
    print(f"   Method: {args.method}")
    print(f"   Data: {args.data_dir}")
    print()
    
    # TODO: Implement query functionality
    print("⚠️  Query command not yet implemented.")
    print("   Use the Gradio interface or API for queries.")
    return 0


# --- DEMO COMMAND ---
def cmd_demo(args: argparse.Namespace) -> int:
    import os
    print(f"🚀 Running VeritasGraph demo")
    print(f"   Mode: {args.mode}")
    if args.model:
        print(f"   Model: {args.model}")

    if args.mode == "lite":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "sk-...":
            print("❌ Please set your OPENAI_API_KEY environment variable for lite mode.")
            return 1
        print("🌐 Using cloud APIs (OpenAI/Anthropic). Zero local setup required.")
        print("   Launching demo pipeline...")
        # Here you would call the appropriate pipeline or server for lite mode
        print("⚠️  Demo pipeline for lite mode not yet implemented. Use the Gradio UI or API.")
        return 0
    elif args.mode == "local":
        print("🖥️  Using local Ollama models. 100% offline.")
        if args.model:
            print(f"   Launching with model: {args.model}")
        else:
            print("   Using default local model.")
        # Here you would call the appropriate pipeline or server for local mode
        print("⚠️  Demo pipeline for local mode not yet implemented. Use the Gradio UI or API.")
        return 0
    else:
        print(f"❌ Unknown demo mode: {args.mode}")
        return 1


# --- START COMMAND ---
def cmd_start(args: argparse.Namespace) -> int:
    print(f"🚀 Starting VeritasGraph in full mode (complete GraphRAG pipeline)")
    # Here you would launch the full pipeline (API server, background workers, etc.)
    print("⚠️  Full pipeline startup not yet implemented. Use 'veritasgraph serve' or the Gradio UI for now.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the API server."""
    print(f"🚀 Starting VeritasGraph API server...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print()
    
    # TODO: Implement server startup
    print("⚠️  Server command not yet fully implemented.")
    print("   Use the graphrag-ollama-config/app.py for now:")
    print("   cd graphrag-ollama-config && python app.py")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new VeritasGraph project."""
    project_path = Path(args.path).resolve()
    
    print(f"📁 Initializing VeritasGraph project in: {project_path}")
    
    # Create directory structure
    dirs = [
        "input",
        "output",
        "cache",
        "prompts",
    ]
    
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
        print(f"   Created: {d}/")
    
    # Create settings file
    settings_content = """# VeritasGraph Settings
# See: https://github.com/bibinprathap/VeritasGraph

encoding_model: cl100k_base
skip_workflows: []
llm:
  api_key: ${GRAPHRAG_API_KEY}
  type: openai_chat
  model: qwen3:8b
  model_supports_json: true
  api_base: http://localhost:11434/v1

embeddings:
  async_mode: threaded
  llm:
    api_key: ${GRAPHRAG_API_KEY}
    type: openai_embedding
    model: nomic-embed-text:latest
    api_base: http://localhost:11434/v1

input:
  type: file
  file_type: text
  base_dir: "input"

cache:
  type: file
  base_dir: "cache"

storage:
  type: file
  base_dir: "output"

reporting:
  type: file
  base_dir: "output/reports"
"""
    
    settings_path = project_path / "settings.yaml"
    if not settings_path.exists():
        settings_path.write_text(settings_content)
        print(f"   Created: settings.yaml")
    else:
        print(f"   Skipped: settings.yaml (already exists)")
    
    # Create .env file
    env_content = """# VeritasGraph Environment Variables
GRAPHRAG_API_KEY=ollama
OLLAMA_HOST=http://localhost:11434
"""
    
    env_path = project_path / ".env"
    if not env_path.exists():
        env_path.write_text(env_content)
        print(f"   Created: .env")
    else:
        print(f"   Skipped: .env (already exists)")
    
    print()
    print("✅ Project initialized!")
    print()
    print("Next steps:")
    print("  1. Add your documents to the 'input/' directory")
    print("  2. Run: veritasgraph ingest input/")
    print("  3. Run: veritasgraph query 'Your question here'")
    
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    commands = {
        "info": cmd_info,
        "ingest": cmd_ingest,
        "query": cmd_query,
        "serve": cmd_serve,
        "init": cmd_init,
        "demo": cmd_demo,
        "start": cmd_start,
    }
    
    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            return 130
        except Exception as e:
            if args.verbose:
                import traceback
                traceback.print_exc()
            else:
                print(f"❌ Error: {e}")
            return 1
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
