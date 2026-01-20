"""
Power BI Authentication Helper
Supports both Service Principal (client credentials) and Device Code flows
"""
import logging
import os
from typing import Optional

from msal import ConfidentialClientApplication, PublicClientApplication

logger = logging.getLogger(__name__)

# Power BI API scope
POWERBI_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]


def get_access_token_service_principal(
    client_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Optional[str]:
    """
    Get Power BI access token using Service Principal (client credentials flow).
    No interactive login required.
    
    Args:
        client_id: Azure AD App Client ID
        tenant_id: Azure AD Tenant ID
        client_secret: Azure AD App Client Secret
    
    Returns:
        Access token string or None if failed
    """
    client_id = client_id or os.getenv("CLIENT_ID")
    tenant_id = tenant_id or os.getenv("TENANT_ID")
    client_secret = client_secret or os.getenv("CLIENT_SECRET")
    
    if not all([client_id, tenant_id, client_secret]):
        logger.error("Missing required credentials: CLIENT_ID, TENANT_ID, or CLIENT_SECRET")
        return None
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    try:
        app = ConfidentialClientApplication(
            client_id=client_id,
            authority=authority,
            client_credential=client_secret,
        )
        
        # Acquire token using client credentials flow (no user interaction)
        result = app.acquire_token_for_client(scopes=POWERBI_SCOPE)
        
        if "access_token" in result:
            logger.info("Successfully acquired access token via Service Principal")
            return result["access_token"]
        else:
            error = result.get("error", "Unknown error")
            error_desc = result.get("error_description", "No description")
            logger.error(f"Failed to acquire token: {error} - {error_desc}")
            return None
            
    except Exception as e:
        logger.error(f"Exception during token acquisition: {str(e)}")
        return None


def get_access_token_device_code(
    client_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """
    Get Power BI access token using Device Code flow (interactive login).
    
    Args:
        client_id: Azure AD App Client ID
        tenant_id: Azure AD Tenant ID
    
    Returns:
        Access token string or None if failed
    """
    client_id = client_id or os.getenv("CLIENT_ID")
    tenant_id = tenant_id or os.getenv("TENANT_ID")
    
    if not all([client_id, tenant_id]):
        logger.error("Missing required credentials: CLIENT_ID or TENANT_ID")
        return None
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    try:
        app = PublicClientApplication(
            client_id=client_id,
            authority=authority,
        )
        
        # Initiate device code flow
        flow = app.initiate_device_flow(scopes=POWERBI_SCOPE)
        
        if "user_code" not in flow:
            logger.error(f"Failed to initiate device flow: {flow.get('error')}")
            return None
        
        print(f"\n🔐 Device Code Authentication Required")
        print(f"   Go to: {flow['verification_uri']}")
        print(f"   Enter code: {flow['user_code']}")
        print(f"   Waiting for authentication...\n")
        
        result = app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            logger.info("Successfully acquired access token via Device Code flow")
            return result["access_token"]
        else:
            error = result.get("error", "Unknown error")
            error_desc = result.get("error_description", "No description")
            logger.error(f"Failed to acquire token: {error} - {error_desc}")
            return None
            
    except Exception as e:
        logger.error(f"Exception during token acquisition: {str(e)}")
        return None


def get_access_token(use_service_principal: bool = True) -> Optional[str]:
    """
    Get Power BI access token using the appropriate flow.
    
    Args:
        use_service_principal: If True, use client credentials flow (no login).
                              If False, use device code flow (interactive login).
    
    Returns:
        Access token string or None if failed
    """
    # Check env var override
    use_sp = os.getenv("USE_SERVICE_PRINCIPAL", str(use_service_principal)).lower() == "true"
    
    if use_sp:
        logger.info("Using Service Principal authentication (no login required)")
        return get_access_token_service_principal()
    else:
        logger.info("Using Device Code authentication (interactive login)")
        return get_access_token_device_code()


if __name__ == "__main__":
    # Quick test
    import sys
    from dotenv import load_dotenv
    
    # Load .env from parent directory
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Service Principal Authentication...")
    token = get_access_token_service_principal()
    
    if token:
        print(f"✅ Success! Token length: {len(token)}")
        print(f"   Token preview: {token[:50]}...")
    else:
        print("❌ Failed to get token")
        sys.exit(1)
