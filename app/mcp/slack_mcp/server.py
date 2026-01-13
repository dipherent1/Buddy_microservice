import os
import json
from pathlib import Path
from typing import Any, Optional, Dict, List, cast
from datetime import datetime

from app.core.logger import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


logger = logging.getLogger(__name__)

TOKEN_PATH = Path(__file__).parent / 'tokens' / 'slack_token.json'

logger.info(f"Using TOKEN_PATH: {TOKEN_PATH}")


# Load environment variables from a local .env if present
def _load_env_file() -> None:
    env_file = Path(__file__).parent / ".env"
    try:
        from dotenv import load_dotenv  # type: ignore
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
    except Exception:
        # Fallback simple parser if python-dotenv isn't installed
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    if k and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass


_load_env_file()


class SlackService:
    """
    Handles Slack API operations using User OAuth Token (xoxp-).
    
    This service uses user tokens to post messages as the authenticated user,
    making messages appear as if sent directly by the user rather than a bot.
    """
    
    def __init__(self):
        self.client: Optional[WebClient] = None
        self.user_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user_name: Optional[str] = None
        self.team_name: Optional[str] = None

    def _ensure_client(self) -> WebClient:
        """Return an initialized Slack WebClient or raise if unauthenticated."""
        if self.client is None:
            raise RuntimeError("Slack client is not initialized. Call authenticate() first.")
        return self.client

    @staticmethod
    def _data(response: Any) -> Dict[str, Any]:
        """Return underlying response data as a dict for Slack SDK responses."""
        return cast(Dict[str, Any], getattr(response, 'data', response) or {})

    def _get_token_from_env(self) -> Optional[str]:
        """Get user token from environment variable"""
        # Priority order for token environment variables
        return (
            os.environ.get("SLACK_USER_TOKEN") or 
            os.environ.get("SLACK_TOKEN") or
            os.environ.get("SLACK_OAUTH_TOKEN")
        )

    def _get_token_from_file(self) -> Optional[str]:
        """Load token from token file"""
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('user_token') or data.get('token')
            except Exception as e:
                logger.warning(f"Failed to load token from file: {e}")
        return None

    def _save_token(self, token: str, user_info: Dict[str, Any]) -> None:
        """Save token and user info to file for persistence"""
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(TOKEN_PATH, 'w', encoding='utf-8') as f:
                json.dump({
                    'user_token': token,
                    'token_type': 'user',
                    'user_id': user_info.get('user_id'),
                    'user_name': user_info.get('user'),
                    'team_name': user_info.get('team'),
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
            logger.info("Slack user token saved successfully")
        except Exception as e:
            logger.warning(f"Failed to save token: {e}")
        
    def authenticate(self) -> bool:
        """
        Authenticate with Slack using User OAuth Token (xoxp-).
        
        This uses a user token which allows posting messages as the authenticated user.
        
        Token sources (priority order):
        1. SLACK_USER_TOKEN environment variable
        2. SLACK_TOKEN environment variable
        3. Token from slack_token.json file
        
        Returns True if authentication successful.
        """
        # Try to get user token from env first
        self.user_token = self._get_token_from_env()
        
        # Fall back to file
        if not self.user_token:
            self.user_token = self._get_token_from_file()
        
        if not self.user_token:
            raise ValueError(
                "Slack user token not found. Please set SLACK_USER_TOKEN environment variable "
                f"or save token to {TOKEN_PATH}.\n\n"
                "To get a user token:\n"
                "1. Go to https://api.slack.com/apps\n"
                "2. Select your app\n"
                "3. Go to 'OAuth & Permissions'\n"
                "4. Under 'User Token Scopes', add required scopes\n"
                "5. Reinstall the app to your workspace\n"
                "6. Copy the 'User OAuth Token' (starts with xoxp-)"
            )
        
        # Verify token starts with xoxp-
        if not self.user_token.startswith('xoxp-'):
            logger.warning(
                "Token does not start with 'xoxp-'. You may have provided a bot token (xoxb-) "
                "instead of a user token. Messages will not appear as sent by the user."
            )
        
        # Initialize Slack client with user token
        self.client = WebClient(token=self.user_token)
        
        # Test authentication and get user info
        try:
            response = self.client.auth_test()
            data = self._data(response)
            self.user_id = cast(Optional[str], data.get('user_id'))
            self.user_name = cast(Optional[str], data.get('user'))
            self.team_name = cast(Optional[str], data.get('team'))
            
            logger.info(
                f"✅ Authenticated as USER: {self.user_name} (ID: {self.user_id}) "
                f"in workspace: {self.team_name}"
            )
            logger.info("📨 Messages will appear as sent by this user")
            
            # Save token to file if it came from env (for future use)
            if self._get_token_from_env() and not TOKEN_PATH.exists():
                self._save_token(self.user_token, {
                    'user_id': self.user_id,
                    'user': self.user_name,
                    'team': self.team_name
                })
            
            return True
        except SlackApiError as e:
            error_msg = e.response.get('error', 'unknown_error')
            if error_msg == 'invalid_auth':
                raise Exception(
                    "Invalid Slack token. Please verify: Please verify"
                )
            elif error_msg == 'token_revoked':
                raise Exception(
                    "Slack token has been revoked. Please generate a new token and update your configuration."
                )
            else:
                raise Exception(f"Failed to authenticate with Slack: {error_msg}")
    
    def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        unfurl_links: bool = True,
        unfurl_media: bool = True
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel or user.
        
        With a user token, this message will appear as sent by the authenticated user.
        
        Args:
            channel: Channel ID, channel name (#general), or user ID for DMs
            text: Message text (supports Slack markdown)
            thread_ts: Thread timestamp to reply in a thread
            blocks: Block Kit blocks for rich formatting
            unfurl_links: Automatically expand links
            unfurl_media: Automatically expand media
        
        Returns:
            dict with message details
        """
        try:
            client = self._ensure_client()
            response = client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                blocks=blocks,
                unfurl_links=unfurl_links,
                unfurl_media=unfurl_media
            )
            
            return {
                'ok': response['ok'],
                'channel': response['channel'],
                'ts': response['ts'],
                'message': response['message'],
                'sent_by_user': self.user_name,
                'status': f'Message sent successfully as {self.user_name}'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'channel_not_found':
                raise Exception(
                    f"Channel not found: {channel}. "
                    "Please verify the channel ID or name is correct."
                )
            elif error == 'not_in_channel':
                raise Exception(
                    f"User {self.user_name} is not a member of channel {channel}. "
                    "Please join the channel first."
                )
            elif error == 'missing_scope':
                raise Exception(
                    "Missing required permission scope. Please add 'chat:write' scope "
                    "to your app's User Token Scopes and reinstall the app."
                )
            else:
                raise Exception(f"Failed to send message: {error}")
    
    def send_dm(
        self,
        user_id: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send a direct message to a user.
        Message will appear as sent by the authenticated user.
        
        Args:
            user_id: User ID to send DM to (format: U1234567890)
            text: Message text
            thread_ts: Thread timestamp for replies
            blocks: Block Kit blocks
        
        Returns:
            dict with message details
        """
        return self.send_message(
            channel=user_id,
            text=text,
            thread_ts=thread_ts,
            blocks=blocks
        )
    
    def list_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 200,
        exclude_archived: bool = True
    ) -> Dict[str, Any]:
        """
        List Slack channels accessible to the authenticated user.
        
        Args:
            types: Channel types (public_channel, private_channel, mpim, im)
            limit: Maximum channels to return
            exclude_archived: Exclude archived channels
        """
        try:
            client = self._ensure_client()
            response = client.conversations_list(
                types=types,
                limit=limit,
                exclude_archived=exclude_archived
            )
            data = self._data(response)
            channels = cast(List[Dict[str, Any]], data.get('channels', []))
            
            return {
                'count': len(channels),
                'user': self.user_name,
                'channels': [
                    {
                        'id': ch['id'],
                        'name': ch['name'],
                        'is_channel': ch.get('is_channel', False),
                        'is_private': ch.get('is_private', False),
                        'is_member': ch.get('is_member', False),
                        'is_archived': ch.get('is_archived', False),
                        'num_members': ch.get('num_members', 0),
                        'topic': ch.get('topic', {}).get('value', ''),
                        'purpose': ch.get('purpose', {}).get('value', ''),
                        'created': ch.get('created', 0)
                    }
                    for ch in channels
                ]
            }
        except SlackApiError as e:
            raise Exception(f"Failed to list channels: {e.response['error']}")
    
    def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        inclusive: bool = True
    ) -> Dict[str, Any]:
        """Get message history from a channel"""
        try:
            client = self._ensure_client()
            response = client.conversations_history(
                channel=channel,
                limit=limit,
                oldest=oldest,
                latest=latest,
                inclusive=inclusive
            )
            data = self._data(response)
            messages = cast(List[Dict[str, Any]], data.get('messages', []))
            
            return {
                'channel': channel,
                'count': len(messages),
                'has_more': bool(self._data(response).get('has_more', False)),
                'messages': [
                    {
                        'type': msg.get('type'),
                        'user': msg.get('user'),
                        'text': msg.get('text'),
                        'ts': msg.get('ts'),
                        'thread_ts': msg.get('thread_ts'),
                        'reply_count': msg.get('reply_count', 0),
                        'reply_users_count': msg.get('reply_users_count', 0),
                        'reactions': msg.get('reactions', []),
                        'edited': msg.get('edited'),
                        'files': msg.get('files', [])
                    }
                    for msg in messages
                ]
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'channel_not_found':
                raise Exception(f"Channel not found: {channel}")
            elif error == 'not_in_channel':
                raise Exception(f"User {self.user_name} is not in channel {channel}")
            else:
                raise Exception(f"Failed to get channel history: {error}")
    
    def get_thread_replies(
        self,
        channel: str,
        thread_ts: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get all replies in a thread"""
        try:
            client = self._ensure_client()
            response = client.conversations_replies(
                channel=channel,
                ts=thread_ts,
                limit=limit
            )
            data = self._data(response)
            messages = cast(List[Dict[str, Any]], data.get('messages', []))
            
            # First message is the parent
            parent = messages[0] if messages else None
            replies = messages[1:] if len(messages) > 1 else []
            
            return {
                'channel': channel,
                'thread_ts': thread_ts,
                'reply_count': len(replies),
                'parent_message': {
                    'user': parent.get('user'),
                    'text': parent.get('text'),
                    'ts': parent.get('ts')
                } if parent else None,
                'replies': [
                    {
                        'user': msg.get('user'),
                        'text': msg.get('text'),
                        'ts': msg.get('ts'),
                        'edited': msg.get('edited')
                    }
                    for msg in replies
                ]
            }
        except SlackApiError as e:
            raise Exception(f"Failed to get thread replies: {e.response['error']}")
    
    def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search for messages across the workspace.
        Results are based on what the authenticated user can access.
        """
        try:
            client = self._ensure_client()
            response = client.search_messages(
                query=query,
                count=count,
                sort=sort,
                sort_dir=sort_dir
            )
            data = self._data(response)
            messages_container = cast(Dict[str, Any], data.get('messages', {}))
            matches = cast(List[Dict[str, Any]], messages_container.get('matches', []))
            
            return {
                'query': query,
                'total': int(messages_container.get('total', 0)),
                'count': len(matches),
                'searched_by': self.user_name,
                'messages': [
                    {
                        'type': msg.get('type'),
                        'user': msg.get('user'),
                        'username': msg.get('username'),
                        'text': msg.get('text'),
                        'ts': msg.get('ts'),
                        'channel': msg.get('channel', {}).get('name'),
                        'channel_id': msg.get('channel', {}).get('id'),
                        'permalink': msg.get('permalink'),
                        'score': msg.get('score')
                    }
                    for msg in matches
                ]
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'missing_scope':
                raise Exception(
                    "Missing 'search:read' scope. Please add it to User Token Scopes "
                    "and reinstall the app."
                )
            else:
                raise Exception(f"Failed to search messages: {error}")
    
    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing message.
        User can only update their own messages.
        """
        try:
            client = self._ensure_client()
            response = client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel': data.get('channel'),
                'ts': data.get('ts'),
                'text': data.get('text'),
                'updated_by': self.user_name,
                'status': 'Message updated successfully'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'cant_update_message':
                raise Exception(
                    f"Cannot update message. User {self.user_name} can only update "
                    "messages they originally sent."
                )
            else:
                raise Exception(f"Failed to update message: {error}")
    
    def delete_message(
        self,
        channel: str,
        ts: str
    ) -> Dict[str, Any]:
        """
        Delete a message.
        User can only delete their own messages.
        """
        try:
            client = self._ensure_client()
            response = client.chat_delete(
                channel=channel,
                ts=ts
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel': data.get('channel'),
                'ts': data.get('ts'),
                'deleted_by': self.user_name,
                'status': 'Message deleted successfully'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'cant_delete_message':
                raise Exception(
                    f"Cannot delete message. User {self.user_name} can only delete "
                    "messages they originally sent, or must have admin privileges."
                )
            else:
                raise Exception(f"Failed to delete message: {error}")
    
    def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Add emoji reaction to a message.
        Reaction will be added by the authenticated user.
        
        Args:
            channel: Channel ID
            timestamp: Message timestamp
            name: Emoji name without colons (e.g., 'thumbsup', 'tada')
        """
        try:
            client = self._ensure_client()
            response = client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'reaction': name,
                'added_by': self.user_name,
                'status': f'Reaction :{name}: added by {self.user_name}'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'already_reacted':
                return {
                    'ok': True,
                    'reaction': name,
                    'added_by': self.user_name,
                    'status': f'User {self.user_name} already reacted with :{name}:'
                }
            elif error == 'missing_scope':
                raise Exception(
                    "Missing 'reactions:write' scope. Please add it to User Token Scopes "
                    "and reinstall the app."
                )
            else:
                raise Exception(f"Failed to add reaction: {error}")
    
    def remove_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> Dict[str, Any]:
        """Remove emoji reaction from a message"""
        try:
            client = self._ensure_client()
            response = client.reactions_remove(
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'reaction': name,
                'removed_by': self.user_name,
                'status': f'Reaction :{name}: removed by {self.user_name}'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'no_reaction':
                return {
                    'ok': True,
                    'reaction': name,
                    'status': f'No reaction :{name}: to remove'
                }
            else:
                raise Exception(f"Failed to remove reaction: {error}")
    
    def list_users(
        self,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List users in the workspace"""
        try:
            client = self._ensure_client()
            response = client.users_list(limit=limit)
            data = self._data(response)
            members = cast(List[Dict[str, Any]], data.get('members', []))
            
            return {
                'count': len(members),
                'workspace': self.team_name,
                'users': [
                    {
                        'id': user['id'],
                        'name': user.get('name'),
                        'real_name': user.get('real_name'),
                        'display_name': user.get('profile', {}).get('display_name'),
                        'email': user.get('profile', {}).get('email'),
                        'title': user.get('profile', {}).get('title'),
                        'phone': user.get('profile', {}).get('phone'),
                        'is_bot': user.get('is_bot', False),
                        'is_admin': user.get('is_admin', False),
                        'is_owner': user.get('is_owner', False),
                        'deleted': user.get('deleted', False)
                    }
                    for user in members
                    if not user.get('deleted', False)
                ]
            }
        except SlackApiError as e:
            raise Exception(f"Failed to list users: {e.response['error']}")
    
    def get_user_info(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get information about a specific user"""
        try:
            client = self._ensure_client()
            response = client.users_info(user=user_id)
            data = self._data(response)
            user = cast(Dict[str, Any], data.get('user', {}))
            
            return {
                'id': user.get('id'),
                'name': user.get('name'),
                'real_name': user.get('real_name'),
                'display_name': user.get('profile', {}).get('display_name'),
                'email': user.get('profile', {}).get('email'),
                'phone': user.get('profile', {}).get('phone'),
                'title': user.get('profile', {}).get('title'),
                'status_text': user.get('profile', {}).get('status_text'),
                'status_emoji': user.get('profile', {}).get('status_emoji'),
                'is_bot': user.get('is_bot', False),
                'is_admin': user.get('is_admin', False),
                'is_owner': user.get('is_owner', False),
                'timezone': user.get('tz'),
                'timezone_label': user.get('tz_label')
            }
        except SlackApiError as e:
            raise Exception(f"Failed to get user info: {e.response['error']}")
    
    def upload_file(
        self,
        channels: str,
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack.
        File will be uploaded by the authenticated user.
        
        Args:
            channels: Comma-separated channel IDs
            file_path: Path to file to upload
            content: File content (alternative to file_path)
            filename: Filename (required when using content)
            title: File title
            initial_comment: Comment to add with file
        """
        try:
            kwargs: Dict[str, Any] = {
                'channels': channels,
                'title': title,
                'initial_comment': initial_comment
            }
            
            if file_path:
                kwargs['file'] = file_path
            elif content:
                kwargs['content'] = content
                if filename:
                    kwargs['filename'] = filename
            else:
                raise ValueError("Either file_path or content must be provided")
            
            client = self._ensure_client()
            response = client.files_upload(**kwargs)
            data = self._data(response)
            file_info = cast(Dict[str, Any], data.get('file', {}))
            
            return {
                'ok': bool(data.get('ok', True)),
                'file_id': file_info.get('id'),
                'name': file_info.get('name'),
                'title': file_info.get('title'),
                'mimetype': file_info.get('mimetype'),
                'size': file_info.get('size'),
                'url_private': file_info.get('url_private'),
                'permalink': file_info.get('permalink'),
                'uploaded_by': self.user_name,
                'status': f'File uploaded successfully by {self.user_name}'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'missing_scope':
                raise Exception(
                    "Missing 'files:write' scope. Please add it to User Token Scopes "
                    "and reinstall the app."
                )
            else:
                raise Exception(f"Failed to upload file: {error}")
    
    def create_channel(
        self,
        name: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new channel.
        Channel will be created by the authenticated user.
        """
        try:
            client = self._ensure_client()
            response = client.conversations_create(
                name=name,
                is_private=is_private
            )
            data = self._data(response)
            channel = cast(Dict[str, Any], data.get('channel', {}))
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel_id': channel.get('id'),
                'channel_name': channel.get('name'),
                'is_private': channel.get('is_private', False),
                'created_by': self.user_name,
                'status': f'Channel created successfully by {self.user_name}'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'name_taken':
                raise Exception(f"Channel name '{name}' is already taken")
            elif error == 'invalid_name':
                raise Exception(
                    f"Invalid channel name '{name}'. Use lowercase letters, numbers, "
                    "hyphens, and underscores only."
                )
            elif error == 'missing_scope':
                raise Exception(
                    "Missing 'channels:manage' or 'groups:write' scope. "
                    "Please add it and reinstall."
                )
            else:
                raise Exception(f"Failed to create channel: {error}")
    
    def invite_to_channel(
        self,
        channel: str,
        users: List[str]
    ) -> Dict[str, Any]:
        """Invite users to a channel"""
        try:
            client = self._ensure_client()
            response = client.conversations_invite(
                channel=channel,
                users=','.join(users)
            )
            data = self._data(response)
            channel_dict = cast(Dict[str, Any], data.get('channel', {}))
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel': channel_dict.get('id'),
                'invited_by': self.user_name,
                'status': f'{self.user_name} invited {len(users)} user(s) to channel'
            }
        except SlackApiError as e:
            error = e.response['error']
            if error == 'already_in_channel':
                raise Exception("One or more users are already in the channel")
            elif error == 'cant_invite_self':
                raise Exception("Cannot invite yourself to a channel")
            elif error == 'user_not_found':
                raise Exception("One or more user IDs are invalid")
            else:
                raise Exception(f"Failed to invite users: {error}")
    
    def set_channel_topic(
        self,
        channel: str,
        topic: str
    ) -> Dict[str, Any]:
        """Set the topic for a channel"""
        try:
            client = self._ensure_client()
            response = client.conversations_setTopic(
                channel=channel,
                topic=topic
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel': data.get('channel'),
                'topic': data.get('topic'),
                'set_by': self.user_name,
                'status': f'Topic set by {self.user_name}'
            }
        except SlackApiError as e:
            raise Exception(f"Failed to set channel topic: {e.response['error']}")
    
    def set_channel_purpose(
        self,
        channel: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Set the purpose/description for a channel"""
        try:
            client = self._ensure_client()
            response = client.conversations_setPurpose(
                channel=channel,
                purpose=purpose
            )
            data = self._data(response)
            
            return {
                'ok': bool(data.get('ok', True)),
                'channel': data.get('channel'),
                'purpose': data.get('purpose'),
                'set_by': self.user_name,
                'status': f'Purpose set by {self.user_name}'
            }
        except SlackApiError as e:
            raise Exception(f"Failed to set channel purpose: {e.response['error']}")