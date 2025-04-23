from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime
import random
import string
from .supabase import get_client

def generate_quest_id() -> str:
    """Generate a 7-character unique quest ID"""
    # Get current timestamp (last 4 digits)
    timestamp = str(int(datetime.now().timestamp()))[-4:]
    # Generate 3 random characters
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{timestamp}{random_chars}"

@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    is_admin: bool = False
    
    @classmethod
    async def get_or_create(cls, telegram_id: int, username: Optional[str] = None, is_admin: bool = False):
        client = get_client()
        user = client.table('users').select('*').eq('telegram_id', telegram_id).single().execute()
        
        if not user.data:
            user = client.table('users').insert({
                'telegram_id': telegram_id,
                'username': username,
                'is_admin': is_admin
            }).execute()
        
        return cls(**user.data[0])

@dataclass
class Quest:
    id: str  # 7-character unique quest ID
    title: str
    description: str
    image_url: Optional[str]  # URL to the quest image
    deadline: Optional[datetime]
    created_by: int  # Admin's telegram_id
    created_at: datetime
    status: str  # 'active', 'completed', 'archived'
    
    @classmethod
    async def create(cls, title: str, description: str, image_url: Optional[str] = None, 
                     deadline: Optional[datetime] = None, created_by: Optional[int] = None):
        client = get_client()
        # Generate a unique 7-character ID
        quest_id = generate_quest_id()
        
        quest = cls(
            id=quest_id,
            title=title,
            description=description,
            image_url=image_url,
            deadline=deadline,
            created_by=created_by,
            created_at=datetime.now(),
            status='active'
        )
        
        quest = client.table('quests').insert({
            'id': quest_id,
            'title': title,
            'description': description,
            'image_url': image_url,
            'deadline': deadline.isoformat() if deadline else None,
            'created_by': created_by,
            'created_at': quest.created_at.isoformat(),
            'status': 'active'
        }).execute()
        
        return cls(**quest.data[0])
    
    @classmethod
    async def get_quest(cls, quest_id: str):
        client = get_client()
        quest = client.table('quests').select('*').eq('id', quest_id).single().execute()
        return cls(**quest.data) if quest.data else None

@dataclass
class QuestSubmission:
    id: str
    quest_id: str
    user_id: int
    submission_text: str
    submission_media: Optional[List[str]]  # URLs to media files
    submitted_at: datetime
    status: str  # 'pending', 'approved', 'denied'
    reviewed_by: Optional[int]  # Admin's telegram_id
    reviewed_at: Optional[datetime]
    
    @classmethod
    async def create(cls, quest_id: str, user_id: int, submission_text: str, submission_media: Optional[List[str]] = None):
        client = get_client()
        # Generate a unique submission ID using the same format as quest ID
        submission_id = f"S{generate_quest_id()}"
        
        submission = client.table('quest_submissions').insert({
            'id': submission_id,
            'quest_id': quest_id,
            'user_id': user_id,
            'submission_text': submission_text,
            'submission_media': submission_media,
            'submitted_at': datetime.now().isoformat(),
            'status': 'pending'
        }).execute()
        
        return cls(**submission.data[0])
    
    @classmethod
    async def get_submission(cls, submission_id: str):
        client = get_client()
        submission = client.table('quest_submissions').select('*').eq('id', submission_id).single().execute()
        return cls(**submission.data) if submission.data else None
    
    async def update_status(self, status: str, reviewed_by: int):
        client = get_client()
        updated = client.table('quest_submissions').update({
            'status': status,
            'reviewed_by': reviewed_by,
            'reviewed_at': datetime.now().isoformat()
        }).eq('id', self.id).execute()
        
        return cls(**updated.data[0])

@dataclass
class UserProgress:
    user_id: int
    quest_id: int
    current_step: int
    completed: bool = False
    
    @classmethod
    async def get_progress(cls, user_id: int, quest_id: int):
        client = get_client()
        progress = client.table('user_progress').select('*').eq('user_id', user_id).eq('quest_id', quest_id).single().execute()
        return cls(**progress.data) if progress.data else None 