import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Group IDs
ADMIN_GROUP_ID = int(os.getenv('ADMIN_GROUP_ID'))
USER_GROUP_ID = int(os.getenv('USER_GROUP_ID'))

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Additional configurations
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Quest configuration
QUEST_ID_PREFIX = "Q"
SUBMISSION_ID_PREFIX = "S" 