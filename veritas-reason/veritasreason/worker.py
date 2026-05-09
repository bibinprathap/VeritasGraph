"""
VeritasReason Worker Entry Point

This module provides the worker process for the VeritasReason framework,
enabling distributed and background task processing.
"""

import time
import signal
import sys
from .utils.logging import get_logger, setup_logging
from .core.orchestrator import VeritasReason

# Initialize logging
setup_logging()
logger = get_logger("veritasreason.worker")

class VeritasReasonWorker:
    """Worker for processing VeritasReason tasks."""
    
    def __init__(self):
        self.framework = VeritasReason()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)
    
    def handle_exit(self, signum, frame):
        """Graceful shutdown."""
        logger.info("Worker shutting down...")
        self.running = False
    
    def run(self):
        """Main worker loop."""
        logger.info("VeritasReason worker started")
        self.running = True
        
        while self.running:
            try:
                # Poll for tasks or process queue
                # logger.debug("Polling for tasks...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(10)
        
        logger.info("Worker stopped")

def main():
    """Worker entry point."""
    worker = VeritasReasonWorker()
    worker.run()

if __name__ == "__main__":
    main()
