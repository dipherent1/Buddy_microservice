import os
import base64
from pathlib import Path
from typing import Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.logger import logging
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# OAuth 2.0 scopes for Gmail
logger = logging.getLogger(__name__)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
]

TOKEN_PATH = Path(__file__).parent / 'tokens' / 'gmail_token.json'
CREDENTIALS_PATH = Path(__file__).parent / 'tokens' / 'credentials.json'

logger.info(f"Using TOKEN_PATH: {TOKEN_PATH}, CREDENTIALS_PATH: {CREDENTIALS_PATH}")


# Load environment variables from a local .env if present
def _load_env_file() -> None:
    env_file = Path(__file__).parent / ".env"
    try:
        from dotenv import load_dotenv  # type: ignore
        # Only load if file exists; don't override existing environment
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


class GmailService:
    """Handles Gmail API operations with OAuth authentication"""
    
    def __init__(self):
        # Use the broad base credentials interface to satisfy all concrete types
        self.creds: Optional[BaseCredentials] = None
        # Lazily constructed Google API client
        self.service: Any = None

    def _get_credentials_path(self) -> Path:
        """Resolve OAuth client secrets path.

        Priority:
        1) GOOGLE_CREDENTIALS_PATH env var (file path)
        2) credentials.json alongside this server.py
        """
        env_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        if env_path:
            # Return the env-provided path even if missing, so errors surface the intended location
            return Path(env_path)
        return CREDENTIALS_PATH
        
    def authenticate(self) -> bool:
        """
        Authenticate user using OAuth 2.0 flow.
        Returns True if authentication successful.
        """
        # Load existing credentials if available
        if TOKEN_PATH.exists():
            self.creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        
        # Refresh or initiate OAuth flow
        if not self.creds or not self.creds.valid:
            if self.creds and getattr(self.creds, "expired", False) and getattr(self.creds, "refresh_token", None):
                self.creds.refresh(Request())
            else:
                cred_path = self._get_credentials_path()
                if not cred_path.exists():
                    env_hint = os.environ.get("GOOGLE_CREDENTIALS_PATH")
                    msg = [
                        "Credentials file not found.",
                        f"Looked for Gmail credentials at: {cred_path}",
                    ]
                    if env_hint:
                        msg.append("GOOGLE_CREDENTIALS_PATH is set but the file was not found at that path.")
                    msg.append(
                        "Set GOOGLE_CREDENTIALS_PATH to your OAuth client secrets JSON path, "
                        f"or place a 'credentials.json' next to this server at: {CREDENTIALS_PATH}"
                    )
                    raise FileNotFoundError("\n".join(msg))

                flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            if self.creds and hasattr(self.creds, "to_json"):
                with open(TOKEN_PATH, 'w') as token:
                    token.write(getattr(self.creds, "to_json")())
            else:
                print("Warning: OAuth credentials could not be serialized; skipping token cache.")
        
        # Build service
        self.service = build('gmail', 'v1', credentials=self.creds)
        
        return True
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html: bool = False
    ) -> dict:
        """Send an email"""
        try:
            message = MIMEMultipart() if html else MIMEText(body)
            
            message['To'] = to
            message['Subject'] = subject
            
            if cc:
                message['Cc'] = cc
            if bcc:
                message['Bcc'] = bcc
            
            if html:
                message.attach(MIMEText(body, 'html'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'messageId': sent_message['id'],
                'threadId': sent_message['threadId'],
                'to': to,
                'subject': subject,
                'message': 'Email sent successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to send email: {e}")
    
    def list_messages(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        label_ids: Optional[list[str]] = None
    ) -> dict:
        """List messages from Gmail inbox"""
        try:
            params = {
                'userId': 'me',
                'maxResults': max_results
            }
            
            if query:
                params['q'] = query
            
            if label_ids:
                params['labelIds'] = label_ids
            
            results = self.service.users().messages().list(**params).execute()
            messages = results.get('messages', [])
            
            # Get full message details
            detailed_messages = []
            for msg in messages:
                msg_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()
                
                headers = msg_detail.get('payload', {}).get('headers', [])
                header_dict = {h['name']: h['value'] for h in headers}
                
                detailed_messages.append({
                    'id': msg_detail['id'],
                    'threadId': msg_detail['threadId'],
                    'snippet': msg_detail.get('snippet', ''),
                    'from': header_dict.get('From', ''),
                    'to': header_dict.get('To', ''),
                    'subject': header_dict.get('Subject', ''),
                    'date': header_dict.get('Date', ''),
                    'labelIds': msg_detail.get('labelIds', [])
                })
            
            return {
                'count': len(detailed_messages),
                'messages': detailed_messages,
                'resultSizeEstimate': results.get('resultSizeEstimate', 0)
            }
        except HttpError as e:
            raise Exception(f"Failed to list messages: {e}")
    
    def get_message(self, message_id: str, format: str = 'full') -> dict:
        """Get a specific message by ID"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract body
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
            else:
                data = message['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return {
                'id': message['id'],
                'threadId': message['threadId'],
                'labelIds': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'from': header_dict.get('From', ''),
                'to': header_dict.get('To', ''),
                'subject': header_dict.get('Subject', ''),
                'date': header_dict.get('Date', ''),
                'body': body
            }
        except HttpError as e:
            raise Exception(f"Failed to get message: {e}")
    
    def search_messages(self, query: str, max_results: int = 10) -> dict:
        """Search messages using Gmail query syntax"""
        return self.list_messages(max_results=max_results, query=query)
    
    def delete_message(self, message_id: str) -> dict:
        """Delete a message (move to trash)"""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            
            return {
                'messageId': message_id,
                'message': 'Message moved to trash successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to delete message: {e}")
    
    def modify_labels(
        self,
        message_id: str,
        add_labels: Optional[list[str]] = None,
        remove_labels: Optional[list[str]] = None
    ) -> dict:
        """Add or remove labels from a message"""
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels
            
            message = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            
            return {
                'messageId': message['id'],
                'labelIds': message.get('labelIds', []),
                'message': 'Labels modified successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to modify labels: {e}")
    
    def list_labels(self) -> dict:
        """List all labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return {
                'count': len(labels),
                'labels': [
                    {
                        'id': label['id'],
                        'name': label['name'],
                        'type': label.get('type', ''),
                        'messageListVisibility': label.get('messageListVisibility', ''),
                        'labelListVisibility': label.get('labelListVisibility', '')
                    }
                    for label in labels
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to list labels: {e}")
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html: bool = False
    ) -> dict:
        """Create a draft email"""
        try:
            message = MIMEMultipart() if html else MIMEText(body)
            
            message['To'] = to
            message['Subject'] = subject
            
            if cc:
                message['Cc'] = cc
            if bcc:
                message['Bcc'] = bcc
            
            if html:
                message.attach(MIMEText(body, 'html'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {
                'draftId': draft['id'],
                'messageId': draft['message']['id'],
                'to': to,
                'subject': subject,
                'message': 'Draft created successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to create draft: {e}")
    
    def reply_to_message(
        self,
        message_id: str,
        body: str,
        html: bool = False
    ) -> dict:
        """Reply to a message"""
        try:
            # Get original message to extract thread ID and headers
            original = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Message-ID']
            ).execute()
            
            headers = original.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            thread_id = original['threadId']
            original_subject = header_dict.get('Subject', '')
            original_from = header_dict.get('From', '')
            
            # Create reply
            message = MIMEMultipart() if html else MIMEText(body)
            message['To'] = original_from
            message['Subject'] = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject
            message['In-Reply-To'] = header_dict.get('Message-ID', '')
            message['References'] = header_dict.get('Message-ID', '')
            
            if html:
                message.attach(MIMEText(body, 'html'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': thread_id
                }
            ).execute()
            
            return {
                'messageId': sent_message['id'],
                'threadId': sent_message['threadId'],
                'inReplyTo': message_id,
                'message': 'Reply sent successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to reply to message: {e}")