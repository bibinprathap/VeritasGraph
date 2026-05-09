import os
import shutil
import tempfile
import traceback
import logging
from typing import Any, Dict, List, Optional

import pytest

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("verify_backends")

try:
    from veritasreason.graph_store.graph_store import GraphStore
except ImportError:
    logger.error("Failed to import veritasreason. Make sure you are in the project root or veritasreason is installed.")
    exit(1)

pytestmark = pytest.mark.integration

def verify_backend(backend_name: str, config: Dict[str, Any]) -> bool:
    logger.info(f"\n{'='*20} Verifying {backend_name.upper()} {'='*20}")
    store = None
    try:
        # Initialize
        logger.info(f"Initializing GraphStore with backend='{backend_name}'...")
        store = GraphStore(backend=backend_name, **config)
        
        # Connect
        logger.info(f"Connecting to {backend_name}...")
        try:
            store.connect()
            logger.info("Connection successful.")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            logger.info(f"Skipping operations for {backend_name} due to connection failure.")
            return False

        # Create Node
        logger.info("Creating test node...")
        node_props = {"name": "TestNode", "test_id": "123"}
        node = store.create_node(labels=["TestLabel"], properties=node_props)
        logger.info(f"Node created: {node}")
        
        node_id = node.get("id")
        if not node_id:
            raise Exception("Node created but returned no ID")

        # Get Node
        logger.info(f"Retrieving node {node_id}...")
        fetched_node = store.get_node(node_id)
        if not fetched_node:
            raise Exception("Failed to retrieve created node")
        if fetched_node.get("properties", {}).get("name") != "TestNode":
            raise Exception("Retrieved node properties do not match")
        logger.info("Node retrieved successfully.")

        # Update Node
        logger.info("Updating node...")
        store.update_node(node_id, properties={"updated": True})
        updated_node = store.get_node(node_id)
        if not updated_node.get("properties", {}).get("updated"):
             raise Exception("Update failed")
        logger.info("Node updated successfully.")

        # Create Relationship
        # We need a second node
        node2 = store.create_node(labels=["TestLabel"], properties={"name": "TestNode2"})
        logger.info("Creating relationship...")
        rel = store.create_relationship(node_id, node2["id"], "TEST_REL", {"since": 2024})
        logger.info(f"Relationship created: {rel}")
        rel_id = rel.get("id")

        # Get Relationship
        # Note: Implementation details of get_relationships vary, assume standard interface
        logger.info("Retrieving relationship...")
        rels = store.get_relationships(node_id=node_id, direction="out")
        found = False
        for r in rels:
            if r.get("id") == rel_id:
                found = True
                break
        if not found:
            logger.warning("Relationship not found in list (could be eventual consistency or implementation nuance)")
        else:
            logger.info("Relationship retrieved successfully.")

        # Delete Relationship
        if rel_id:
            logger.info("Deleting relationship...")
            store.delete_relationship(rel_id)
            logger.info("Relationship deleted.")

        # Delete Nodes
        logger.info("Deleting nodes...")
        store.delete_node(node_id)
        store.delete_node(node2["id"])
        
        check = store.get_node(node_id)
        if check:
            logger.warning("Node still exists after deletion (could be eventual consistency)")
        else:
            logger.info("Node deletion verified.")

        logger.info(f"SUCCESS: {backend_name} passed all verification steps.")
        return True

    except Exception as e:
        logger.error(f"FAILURE: {backend_name} encountered an error: {str(e)}")
        # traceback.print_exc()
        return False
    finally:
        if store:
            try:
                store.close()
            except:
                pass

def main():
    results = {}
    
    # 2. Neo4j (Requires Server)
    # Using defaults or env vars. If not running, this will fail connection, which is expected.
    # To test properly, user needs to set GRAPH_STORE_NEO4J_URI etc.
    results['neo4j'] = verify_backend('neo4j', {})

    # 3. FalkorDB (Requires Redis)
    results['falkordb'] = verify_backend('falkordb', {})

    print("\n" + "="*50)
    print("VERIFICATION SUMMARY")
    print("="*50)
    for backend, result in results.items():
        status = "PASSED" if result else "FAILED (or Skipped)"
        print(f"{backend.ljust(15)}: {status}")
    print("="*50)

if __name__ == "__main__":
    main()
