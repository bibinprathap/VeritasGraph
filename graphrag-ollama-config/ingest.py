"""
Instant Knowledge Ingest Module
Handles YouTube and Web Article URL ingestion for VeritasGraph.
"""

import os
import re
import subprocess
import hashlib
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Tuple, Optional
import json

# YouTube transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, 
        NoTranscriptFound, 
        VideoUnavailable
    )
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# Web article extraction
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

# Get the script directory for input folder path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")


def ensure_input_dir():
    """Ensure input directory exists."""
    os.makedirs(INPUT_DIR, exist_ok=True)


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    """
    if not url:
        return None
    
    # Parse the URL
    parsed = urlparse(url)
    
    # youtu.be format
    if parsed.netloc in ['youtu.be', 'www.youtu.be']:
        return parsed.path.lstrip('/')
    
    # youtube.com formats
    if parsed.netloc in ['youtube.com', 'www.youtube.com', 'm.youtube.com']:
        # Standard watch URL
        if parsed.path == '/watch':
            query_params = parse_qs(parsed.query)
            return query_params.get('v', [None])[0]
        
        # Embed or v format
        if parsed.path.startswith('/embed/') or parsed.path.startswith('/v/'):
            return parsed.path.split('/')[2]
    
    return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video URL."""
    return extract_youtube_video_id(url) is not None


def get_youtube_transcript(video_id: str) -> Tuple[bool, str, Optional[dict]]:
    """
    Fetch transcript from a YouTube video.
    
    Returns:
        Tuple of (success, content_or_error, metadata)
    """
    if not YOUTUBE_AVAILABLE:
        return False, "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api", None
    
    try:
        # New API (v1.x): Instantiate and use fetch method
        api = YouTubeTranscriptApi()
        transcript_data = None
        transcript_type = "auto-detected"
        
        try:
            # Fetch transcript (auto-selects best available)
            transcript_data = api.fetch(video_id)
        except Exception as e:
            error_msg = str(e)
            # Check if it's a "no transcripts" situation
            if "No transcripts" in error_msg or "disabled" in error_msg.lower():
                return False, f"This video has no transcripts/captions available. Try a video with CC enabled.", None
            elif "Video unavailable" in error_msg or "unavailable" in error_msg.lower():
                return False, "Video is unavailable, private, or does not exist.", None
            else:
                return False, f"Could not fetch transcript: {error_msg}", None
        
        if transcript_data is None or len(transcript_data) == 0:
            return False, "No suitable transcript found for this video. The video may not have captions enabled.", None
        
        # Combine transcript segments into readable text
        # New API returns FetchedTranscriptSnippet objects with .text attribute
        full_text = []
        for segment in transcript_data:
            # Handle both old dict format and new object format
            if hasattr(segment, 'text'):
                text = segment.text.strip()
            elif isinstance(segment, dict):
                text = segment.get('text', '').strip()
            else:
                text = str(segment).strip()
            if text:
                full_text.append(text)
        
        combined_text = ' '.join(full_text)
        
        # Clean up the text
        combined_text = re.sub(r'\s+', ' ', combined_text)  # Normalize whitespace
        combined_text = combined_text.replace('[Music]', '').replace('[Applause]', '')
        combined_text = re.sub(r'\[.*?\]', '', combined_text)  # Remove other bracketed content
        
        if len(combined_text.strip()) < 50:
            return False, "Transcript is too short or empty. The video may only have music/non-speech content.", None
        
        metadata = {
            "video_id": video_id,
            "transcript_type": transcript_type,
            "segment_count": len(transcript_data),
            "character_count": len(combined_text),
            "word_count": len(combined_text.split())
        }
        
        return True, combined_text, metadata
        
    except TranscriptsDisabled:
        return False, "Transcripts are disabled for this video by the uploader.", None
    except NoTranscriptFound:
        return False, "No transcript/captions found for this video.", None
    except VideoUnavailable:
        return False, "Video is unavailable, private, or does not exist.", None
    except Exception as e:
        return False, f"Error fetching transcript: {str(e)}", None


def get_youtube_metadata(video_id: str) -> dict:
    """
    Get basic metadata for a YouTube video using yt-dlp.
    
    Returns dict with title, description, channel, etc.
    """
    try:
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '--dump-json', '--skip-download', f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", "Unknown Title"),
                "channel": data.get("channel", data.get("uploader", "Unknown")),
                "description": data.get("description", "")[:500],
                "duration": data.get("duration", 0),
                "upload_date": data.get("upload_date", ""),
                "view_count": data.get("view_count", 0)
            }
    except:
        pass
    
    return {"title": f"YouTube Video {video_id}", "channel": "Unknown"}


def extract_web_article(url: str) -> Tuple[bool, str, Optional[dict]]:
    """
    Extract main content from a web article URL.
    
    Returns:
        Tuple of (success, content_or_error, metadata)
    """
    if not TRAFILATURA_AVAILABLE:
        return False, "trafilatura is not installed. Run: pip install trafilatura", None
    
    try:
        # Download the page
        downloaded = trafilatura.fetch_url(url)
        
        if downloaded is None:
            return False, "Could not download the webpage. Please check the URL.", None
        
        # Extract the main content
        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=False,
            output_format='txt'
        )
        
        if not content or len(content.strip()) < 100:
            return False, "Could not extract meaningful content from this page. It may be blocked or require JavaScript.", None
        
        # Try to extract metadata
        metadata_result = trafilatura.extract(
            downloaded,
            output_format='json',
            include_comments=False
        )
        
        metadata = {"url": url}
        if metadata_result:
            try:
                meta_json = json.loads(metadata_result)
                metadata.update({
                    "title": meta_json.get("title", "Unknown Title"),
                    "author": meta_json.get("author", "Unknown"),
                    "date": meta_json.get("date", ""),
                    "sitename": meta_json.get("sitename", urlparse(url).netloc)
                })
            except:
                metadata["title"] = urlparse(url).netloc
        
        metadata["character_count"] = len(content)
        metadata["word_count"] = len(content.split())
        
        return True, content, metadata
        
    except Exception as e:
        return False, f"Error extracting article: {str(e)}", None


def generate_filename(url: str, content_type: str, metadata: Optional[dict] = None) -> str:
    """
    Generate a descriptive filename for the ingested content.
    
    Format: {type}_{safe_title}_{short_hash}.txt
    """
    # Create a short hash from the URL for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    
    # Get title from metadata or derive from URL
    if metadata and metadata.get("title"):
        title = metadata["title"]
    elif content_type == "youtube":
        video_id = extract_youtube_video_id(url) or "video"
        title = f"youtube_{video_id}"
    else:
        # Use domain + path for articles
        parsed = urlparse(url)
        title = f"{parsed.netloc}_{parsed.path}"
    
    # Clean title for filename
    safe_title = re.sub(r'[^\w\s-]', '', title)
    safe_title = re.sub(r'[-\s]+', '_', safe_title)
    safe_title = safe_title[:50]  # Limit length
    
    return f"{content_type}_{safe_title}_{url_hash}.txt"


def format_content_for_graphrag(content: str, metadata: dict, source_type: str) -> str:
    """
    Format the content with metadata header for better GraphRAG indexing.
    """
    header_lines = [
        f"# Source: {source_type.upper()}",
        f"# Title: {metadata.get('title', 'Unknown')}",
    ]
    
    if source_type == "youtube":
        header_lines.extend([
            f"# Channel: {metadata.get('channel', 'Unknown')}",
            f"# Video ID: {metadata.get('video_id', 'Unknown')}",
        ])
        if metadata.get('duration'):
            duration_min = metadata.get('duration', 0) // 60
            header_lines.append(f"# Duration: {duration_min} minutes")
    else:
        header_lines.extend([
            f"# URL: {metadata.get('url', 'Unknown')}",
            f"# Author: {metadata.get('author', 'Unknown')}",
            f"# Site: {metadata.get('sitename', 'Unknown')}",
        ])
    
    header_lines.extend([
        f"# Ingested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Word Count: {metadata.get('word_count', 'Unknown')}",
        "",
        "---",
        ""
    ])
    
    return '\n'.join(header_lines) + content


def save_content(filename: str, content: str) -> str:
    """
    Save content to the input directory.
    
    Returns the full path to the saved file.
    """
    ensure_input_dir()
    filepath = os.path.join(INPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def ingest_url(url: str, auto_index: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Main function to ingest content from a URL.
    
    Args:
        url: YouTube or web article URL
        auto_index: If True, automatically trigger GraphRAG indexing
    
    Returns:
        Tuple of (success, message, filepath)
    """
    url = url.strip()
    
    if not url:
        return False, "Please provide a URL.", None
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Determine content type and extract
    if is_youtube_url(url):
        video_id = extract_youtube_video_id(url)
        
        # Get video metadata first
        yt_metadata = get_youtube_metadata(video_id)
        
        # Get transcript
        success, content, transcript_meta = get_youtube_transcript(video_id)
        
        if not success:
            return False, f"❌ YouTube Error: {content}", None
        
        # Merge metadata
        metadata = {**yt_metadata, **(transcript_meta or {})}
        content_type = "youtube"
        
    else:
        # Treat as web article
        success, content, metadata = extract_web_article(url)
        
        if not success:
            return False, f"❌ Article Error: {content}", None
        
        content_type = "article"
    
    # Generate filename and format content
    filename = generate_filename(url, content_type, metadata)
    formatted_content = format_content_for_graphrag(content, metadata, content_type)
    
    # Save to input directory
    filepath = save_content(filename, formatted_content)
    
    # Build success message
    title = metadata.get('title', 'Unknown')
    word_count = metadata.get('word_count', len(content.split()))
    
    message_parts = [
        f"✅ **Successfully ingested!**",
        f"",
        f"📄 **Title:** {title}",
        f"📊 **Words:** {word_count:,}",
        f"💾 **Saved to:** `{filename}`",
        f"",
    ]
    
    if content_type == "youtube":
        if metadata.get('duration'):
            message_parts.insert(3, f"⏱️ **Duration:** {metadata['duration'] // 60} minutes")
        message_parts.insert(3, f"📺 **Channel:** {metadata.get('channel', 'Unknown')}")
    else:
        message_parts.insert(3, f"🌐 **Site:** {metadata.get('sitename', 'Unknown')}")
    
    message_parts.append("🔄 **Next:** Click 'Index Now' to add this to your knowledge graph!")
    
    message = '\n'.join(message_parts)
    
    # Auto-index if requested
    if auto_index:
        index_success, index_msg = trigger_graphrag_index()
        message += f"\n\n{index_msg}"
    
    return True, message, filepath


def ingest_text_content(title: str, content: str, auto_index: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Ingest raw text content directly (copy-pasted from files, documents, etc.).
    
    Args:
        title: Title for the content (used in filename and metadata)
        content: The raw text content to ingest
        auto_index: If True, automatically trigger GraphRAG indexing
    
    Returns:
        Tuple of (success, message, filepath)
    """
    # Validate inputs
    if not title or not title.strip():
        return False, "⚠️ Please provide a title for the content.", None
    
    if not content or not content.strip():
        return False, "⚠️ Please provide some text content to ingest.", None
    
    title = title.strip()
    content = content.strip()
    
    # Check minimum content length
    if len(content) < 50:
        return False, "⚠️ Content is too short. Please provide at least 50 characters of meaningful text.", None
    
    # Generate filename
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    safe_title = re.sub(r'[^\w\s-]', '', title)
    safe_title = re.sub(r'[-\s]+', '_', safe_title)
    safe_title = safe_title[:50]  # Limit length
    filename = f"text_{safe_title}_{content_hash}.txt"
    
    # Build metadata
    metadata = {
        "title": title,
        "source": "direct_text_input",
        "word_count": len(content.split()),
        "character_count": len(content)
    }
    
    # Format content with header
    header_lines = [
        f"# Source: DIRECT TEXT INPUT",
        f"# Title: {title}",
        f"# Ingested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Word Count: {metadata['word_count']}",
        f"# Character Count: {metadata['character_count']}",
        "",
        "---",
        ""
    ]
    formatted_content = '\n'.join(header_lines) + content
    
    # Save to input directory
    filepath = save_content(filename, formatted_content)
    
    # Build success message
    message_parts = [
        f"✅ **Successfully ingested text content!**",
        f"",
        f"📄 **Title:** {title}",
        f"📊 **Words:** {metadata['word_count']:,}",
        f"📝 **Characters:** {metadata['character_count']:,}",
        f"💾 **Saved to:** `{filename}`",
        f"",
        f"🔄 **Next:** Click 'Full Index' or 'Update Index' to add this to your knowledge graph!"
    ]
    
    message = '\n'.join(message_parts)
    
    # Auto-index if requested
    if auto_index:
        index_success, index_msg = trigger_graphrag_index()
        message += f"\n\n{index_msg}"
    
    return True, message, filepath


def trigger_graphrag_index_async() -> Tuple[bool, str]:
    """
    Start GraphRAG indexing process in background.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        import sys
        python_exe = sys.executable
        
        cmd = [python_exe, "-m", "graphrag.index", "--root", SCRIPT_DIR]
        
        # Start process in background
        process = subprocess.Popen(
            cmd,
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait briefly to check for immediate errors
        try:
            stdout, stderr = process.communicate(timeout=3)
            if process.returncode != 0:
                return False, f"❌ Indexing failed: {stderr[:500]}"
        except subprocess.TimeoutExpired:
            pass  # Still running, which is expected
        
        return True, "🔄 **Indexing started in background!**"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_indexing_status() -> Tuple[str, bool]:
    """
    Check the current indexing status by reading the log file.
    
    Returns:
        Tuple of (status_message, is_complete)
    """
    log_path = os.path.join(SCRIPT_DIR, "output", "reports", "indexing-engine.log")
    docs_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_documents.parquet")
    entities_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_entities.parquet")
    
    if not os.path.exists(log_path):
        return "⏳ No indexing log found. Click **Index Now** to start indexing.", False
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.strip().split('\n')
            
        if not lines:
            return "⏳ Indexing starting...", False
        
        # Check for completion
        if "All workflows completed successfully" in content:
            # Get stats
            doc_count = "unknown"
            entity_count = "unknown"
            try:
                import pandas as pd
                if os.path.exists(docs_path):
                    df = pd.read_parquet(docs_path)
                    doc_count = len(df)
                if os.path.exists(entities_path):
                    df = pd.read_parquet(entities_path)
                    entity_count = len(df)
            except:
                pass
            
            return f"""✅ **Indexing completed successfully!**

📊 **Current Index Stats:**
- 📄 Documents: **{doc_count}**
- 🏷️ Entities: **{entity_count}**

🎉 Ready to query! Switch to the **Chat** tab.""", True
        
        # Check for errors
        if "Error" in lines[-1] or "Exception" in lines[-1]:
            return f"❌ Error detected: {lines[-1][:200]}", True
        
        # Define workflow stages for better progress display
        workflow_stages = {
            "create_base_text_units": "📝 Chunking text into units",
            "create_base_extracted_entities": "🔍 Extracting entities",
            "create_summarized_entities": "📋 Summarizing descriptions",
            "create_base_entity_graph": "🕸️ Building entity graph",
            "create_final_entities": "✨ Finalizing entities",
            "create_final_nodes": "📍 Creating graph nodes",
            "create_final_communities": "👥 Detecting communities",
            "create_final_relationships": "🔗 Finalizing relationships",
            "create_final_text_units": "📄 Finalizing text units",
            "create_final_community_reports": "📊 Generating community reports",
            "create_base_documents": "📚 Processing documents",
            "create_final_documents": "✅ Finalizing documents"
        }
        
        # Find latest workflow stage
        current_stage = "🔄 Initializing..."
        for stage, desc in workflow_stages.items():
            if stage in content:
                current_stage = desc
        
        return f"⏳ **Indexing in progress...**\n\n{current_stage}", False
            
    except Exception as e:
        return f"⚠️ Could not read log: {str(e)}", False


def trigger_graphrag_index_with_progress(update_mode: bool = False):
    """
    Generator function that triggers GraphRAG indexing and yields progress updates.
    
    Args:
        update_mode: If True, use --update-index flag for incremental indexing
    
    Yields:
        str: Progress messages to display in the UI
    """
    import sys
    import time
    python_exe = sys.executable
    
    log_path = os.path.join(SCRIPT_DIR, "output", "reports", "indexing-engine.log")
    
    # Count input files first
    input_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    file_count = len(input_files)
    
    # Build command
    cmd = [python_exe, "-m", "graphrag.index", "--root", SCRIPT_DIR, "--reporter", "print"]
    
    # For update mode, find the last run ID
    index_type = "Full"
    if update_mode:
        last_run_id = get_last_run_id()
        if last_run_id:
            cmd.extend(["--update-index", last_run_id])
            index_type = "Update"
            yield f"🔄 **Starting Update Index**\n\n📁 Found **{file_count}** text files in input folder\n🔗 Using previous run: `{last_run_id}`\n\n⏳ Initializing..."
        else:
            yield f"🚀 **Starting Full Index** (no previous run found)\n\n📁 Found **{file_count}** text files in input folder\n\n⏳ Initializing..."
    else:
        # Clear old log for full reindex
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
            except:
                pass
        yield f"🚀 **Starting Full GraphRAG Index**\n\n📁 Found **{file_count}** text files in input folder\n\n⏳ Initializing..."
    
    try:
        # Start process
        process = subprocess.Popen(
            cmd,
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        max_wait_seconds = 1200  # 20 minutes max
        start_time = time.time()
        last_log_size = 0
        workflow_stages = {
            "create_base_text_units": "📝 Chunking text into units...",
            "create_base_extracted_entities": "🔍 Extracting entities (this takes a while)...",
            "create_summarized_entities": "📋 Summarizing entity descriptions...",
            "create_base_entity_graph": "🕸️ Building entity graph...",
            "create_final_entities": "✨ Finalizing entities...",
            "create_final_nodes": "📍 Creating graph nodes...",
            "create_final_communities": "👥 Detecting communities...",
            "create_final_relationships": "🔗 Finalizing relationships...",
            "create_final_text_units": "📄 Finalizing text units...",
            "create_final_community_reports": "📊 Generating community reports (this takes a while)...",
            "create_base_documents": "📚 Processing documents...",
            "create_final_documents": "✅ Finalizing documents..."
        }
        current_stage = "Initializing..."
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                process.terminate()
                yield "❌ **Indexing timed out after 20 minutes.** Check logs for issues."
                return
            
            # Read log file for progress
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Check for workflow stages
                    for stage, desc in workflow_stages.items():
                        if stage in content and desc != current_stage:
                            current_stage = desc
                            elapsed_min = elapsed / 60
                            yield f"🔄 **{index_type} Indexing in progress** ({elapsed_min:.1f} min)\n\n{current_stage}\n\n📁 Processing {file_count} files..."
                    
                except:
                    pass
            
            time.sleep(3)
        
        # Process completed
        stdout_rest, _ = process.communicate()
        
        if process.returncode == 0:
            # Verify success and get stats
            docs_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_documents.parquet")
            entities_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_entities.parquet")
            
            doc_count = "unknown"
            entity_count = "unknown"
            
            try:
                import pandas as pd
                if os.path.exists(docs_path):
                    df = pd.read_parquet(docs_path)
                    doc_count = len(df)
                if os.path.exists(entities_path):
                    df = pd.read_parquet(entities_path)
                    entity_count = len(df)
            except:
                pass
            
            elapsed_total = (time.time() - start_time) / 60
            index_emoji = "🔄" if update_mode else "📊"
            yield f"""✅ **{index_emoji} {index_type} Indexing completed successfully!**

📊 **Results:**
- 📄 Documents indexed: **{doc_count}**
- 🏷️ Entities extracted: **{entity_count}**
- ⏱️ Time taken: **{elapsed_total:.1f} minutes**

🎉 Your knowledge graph is now ready! Switch to the **Chat** tab to query your data."""
        else:
            yield f"❌ **Indexing failed** (exit code: {process.returncode})\n\nCheck the logs at:\n`output/reports/indexing-engine.log`"
            
    except FileNotFoundError:
        yield "❌ **GraphRAG not found.** Make sure graphrag is installed."
    except Exception as e:
        yield f"❌ **Error:** {str(e)}"


def get_last_run_id() -> Optional[str]:
    """
    Extract the last run ID from the indexing log file.
    
    Returns:
        The run ID (e.g., '20260113-090657') or None if not found
    """
    log_path = os.path.join(SCRIPT_DIR, "output", "reports", "indexing-engine.log")
    
    if not os.path.exists(log_path):
        return None
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for: "Starting pipeline run for: 20260113-090657"
                if "Starting pipeline run for:" in line:
                    match = re.search(r'run for:\s*(\d{8}-\d{6})', line)
                    if match:
                        return match.group(1)
    except:
        pass
    
    return None


def trigger_graphrag_index(update_mode: bool = False) -> Tuple[bool, str]:
    """
    Trigger GraphRAG indexing process and wait for completion.
    
    Args:
        update_mode: If True, use --update-index flag for incremental indexing
    
    Returns:
        Tuple of (success, message)
    """
    try:
        import sys
        import time
        python_exe = sys.executable
        
        # Build command
        cmd = [python_exe, "-m", "graphrag.index", "--root", SCRIPT_DIR, "--reporter", "print"]
        
        # For update mode, find the last run ID and use --update-index
        if update_mode:
            last_run_id = get_last_run_id()
            if last_run_id:
                cmd.extend(["--update-index", last_run_id])
            else:
                # No previous run found, fall back to full index
                update_mode = False
        
        # Clear old log for fresh progress tracking
        log_path = os.path.join(SCRIPT_DIR, "output", "reports", "indexing-engine.log")
        
        # Start process
        process = subprocess.Popen(
            cmd,
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for process to complete (with timeout)
        max_wait_seconds = 1200  # 20 minutes max
        start_time = time.time()
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                process.terminate()
                return False, "❌ Indexing timed out after 20 minutes. Check logs for issues."
            time.sleep(2)
        
        # Process completed
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Verify by checking log
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                if "All workflows completed successfully" in log_content:
                    # Count documents
                    docs_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_documents.parquet")
                    entities_path = os.path.join(SCRIPT_DIR, "output", "artifacts", "create_final_entities.parquet")
                    doc_count = "unknown"
                    entity_count = "unknown"
                    try:
                        import pandas as pd
                        df = pd.read_parquet(docs_path)
                        doc_count = len(df)
                        df = pd.read_parquet(entities_path)
                        entity_count = len(df)
                    except:
                        pass
                    
                    index_type = "🔄 Update" if update_mode else "📊 Full"
                    return True, f"✅ **{index_type} Indexing completed successfully!**\n\n📄 **Documents indexed:** {doc_count}\n🏷️ **Entities:** {entity_count}\n\n🎉 You can now chat with your knowledge graph!"
            
            return True, "✅ **Indexing completed!** Refresh the page to query your new data."
        else:
            error_msg = stderr[:500] if stderr else "Unknown error"
            return False, f"❌ Indexing failed:\n\n```\n{error_msg}\n```"
        
    except FileNotFoundError:
        return False, "❌ GraphRAG not found. Make sure graphrag is installed."
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def list_input_files() -> list:
    """List all files in the input directory."""
    ensure_input_dir()
    files = []
    for f in os.listdir(INPUT_DIR):
        if f.endswith('.txt'):
            filepath = os.path.join(INPUT_DIR, f)
            stat = os.stat(filepath)
            files.append({
                "name": f,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            })
    return sorted(files, key=lambda x: x['modified'], reverse=True)


def delete_input_file(filename: str) -> Tuple[bool, str]:
    """Delete a file from the input directory."""
    filepath = os.path.join(INPUT_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True, f"✅ Deleted: {filename}"
    return False, f"❌ File not found: {filename}"


def get_file_preview(filename: str, max_chars: int = 1000) -> str:
    """Get a preview of file contents."""
    filepath = os.path.join(INPUT_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(max_chars)
            if len(content) == max_chars:
                content += "\n\n... (truncated)"
            return content
    return "File not found"


# Check dependencies on module load
def check_dependencies() -> dict:
    """Check which optional dependencies are available."""
    return {
        "youtube": YOUTUBE_AVAILABLE,
        "web": TRAFILATURA_AVAILABLE
    }
