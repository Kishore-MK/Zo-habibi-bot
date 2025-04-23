from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import uuid
from .supabase import get_client

@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool = False
    points: int = 0
    quests_completed: int = 0
    quests_submitted: int = 0
    created_at: datetime = None
    updated_at: datetime = None

    @classmethod
    async def get_or_create(cls, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, is_admin: bool = False) -> 'User':
        """Get a user by telegram_id or create if not exists"""
        client = get_client()
        
        # Try to get existing user
        result = client.table('users').select('*').eq('telegram_id', telegram_id).execute()
        if result.data:
            user_data = result.data[0]
            return cls(**user_data)
        
        # Create new user if not exists
        now = datetime.utcnow()
        user_data = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'is_admin': is_admin,
            'points': 0,
            'quests_completed': 0,
            'quests_submitted': 0,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        
        result = client.table('users').insert(user_data).execute()
        return cls(**result.data[0])

@dataclass
class Quest:
    id: uuid.UUID
    quest_code: str
    title: str
    description: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    image_url: Optional[str] = None
    deadline: Optional[datetime] = None
    points: int = 10
    is_active: bool = True

    @classmethod
    async def create(cls, title: str, description: str, quest_code: str,
                    created_by: int, image_url: Optional[str] = None, 
                    deadline: Optional[datetime] = None, points: int = 10):
        client = get_client()
        quest = client.table('quests').insert({
            'title': title,
            'description': description,
            'quest_code': quest_code,
            'image_url': image_url,
            'deadline': deadline.isoformat() if deadline else None,
            'points': points,
            'created_by': created_by,
            'is_active': True
        }).execute()
        
        return cls(**quest.data[0])

    @classmethod
    async def get_by_code(cls, quest_code: str):
        client = get_client()
        quest = client.table('quests').select('*').eq('quest_code', quest_code).single().execute()
        return cls(**quest.data[0]) if quest.data else None

    @classmethod
    async def get_active(cls):
        client = get_client()
        quests = client.table('quests').select('*').eq('is_active', True).execute()
        return [cls(**quest) for quest in quests.data]

@dataclass
class Submission:
    id: uuid.UUID
    quest_id: uuid.UUID
    user_id: int
    submission_text: str
    submitted_at: datetime
    updated_at: datetime
    submission_media: Optional[List[str]] = None
    original_message_id: Optional[int] = None
    admin_message_id: Optional[int] = None
    status: str = 'pending'
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    feedback: Optional[str] = None

    @classmethod
    async def create(cls, quest_id: uuid.UUID, user_id: int, submission_text: str,
                    submission_media: Optional[List[str]] = None,
                    original_message_id: Optional[int] = None):
        client = get_client()
        submission = client.table('submissions').insert({
            'quest_id': quest_id,
            'user_id': user_id,
            'submission_text': submission_text,
            'submission_media': submission_media,
            'original_message_id': original_message_id,
            'status': 'pending'
        }).execute()
        
        return cls(**submission.data[0])

    @classmethod
    async def get_by_id(cls, submission_id: uuid.UUID):
        client = get_client()
        submission = client.table('submissions').select('*').eq('id', submission_id).single().execute()
        return cls(**submission.data[0]) if submission.data else None

    async def update_status(self, status: str, reviewed_by: int, feedback: Optional[str] = None):
        client = get_client()
        updated = client.table('submissions').update({
            'status': status,
            'reviewed_by': reviewed_by,
            'reviewed_at': datetime.now().isoformat(),
            'feedback': feedback
        }).eq('id', self.id).execute()
        
        return self.__class__(**updated.data[0])

@dataclass
class LeaderboardEntry:
    user_id: int
    rank: int
    points: int
    quests_completed: int
    last_updated: datetime

    @classmethod
    async def get_leaderboard(cls, limit: int = 10):
        client = get_client()
        entries = client.table('leaderboard').select('*').order('rank').limit(limit).execute()
        return [cls(**entry) for entry in entries.data] 