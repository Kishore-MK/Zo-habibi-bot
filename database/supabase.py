import logging
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Initialize Supabase client
try:
    logger.info(f"Connecting to Supabase at {SUPABASE_URL}")
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {e}")
    raise

def get_client():
    """
    Returns the Supabase client instance
    """
    return supabase_client

async def test_connection():
    """
    Test the Supabase connection
    """
    try:
        client = get_client()
        # Try to list tables
        response = client.table('quests').select('*').limit(1).execute()
        logger.info(f"Supabase connection test successful: {response}")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False 