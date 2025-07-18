"""Session management for MCP Streamable HTTP transport.

This module implements session lifecycle management including session creation,
validation, expiration, and cleanup as specified in MCP 2025-03-26.
"""

import hashlib
import logging
import secrets
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Session:
    """Represents an MCP session with metadata and lifecycle information."""
    
    session_id: str
    created_at: float
    last_accessed: float
    client_info: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, timeout: float = 3600) -> bool:
        """Check if the session has expired based on last access time."""
        return time.time() - self.last_accessed > timeout
    
    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'client_info': self.client_info,
            'capabilities': self.capabilities,
            'context': self.context
        }


class SessionManager:
    """Manages MCP session lifecycle for Streamable HTTP transport."""
    
    def __init__(self, session_timeout: float = 3600, cleanup_interval: float = 300):
        """Initialize session manager.
        
        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
            cleanup_interval: Cleanup interval in seconds (default: 5 minutes)
        """
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.sessions: Dict[str, Session] = {}
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        self.last_cleanup = time.time()
        self.created_at = time.time()  # Track when session manager was created
        
        self.logger.info(f"SessionManager initialized with timeout={session_timeout}s")
    
    def generate_session_id(self) -> str:
        """Generate a cryptographically secure session ID.
        
        Returns:
            Session ID containing only visible ASCII characters (0x21-0x7E)
        """
        # Generate random bytes and create a hash
        random_bytes = secrets.token_bytes(32)
        timestamp = str(time.time()).encode('utf-8')
        
        # Create SHA-256 hash of random bytes + timestamp
        hash_obj = hashlib.sha256(random_bytes + timestamp)
        
        # Convert to hex string (contains only 0-9, a-f)
        session_id = hash_obj.hexdigest()
        
        # Ensure it's within visible ASCII range by using base64url encoding
        # which produces characters in the range [A-Za-z0-9_-]
        import base64
        session_id_bytes = session_id.encode('utf-8')
        session_id = base64.urlsafe_b64encode(session_id_bytes).decode('utf-8').rstrip('=')
        
        self.logger.debug(f"Generated session ID: {session_id[:8]}...")
        return session_id
    
    def create_session(self, client_info: Optional[Dict[str, Any]] = None, 
                      capabilities: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session with generated ID.
        
        Args:
            client_info: Optional client information
            capabilities: Optional client capabilities
            
        Returns:
            New session object
        """
        session_id = self.generate_session_id()
        current_time = time.time()
        
        session = Session(
            session_id=session_id,
            created_at=current_time,
            last_accessed=current_time,
            client_info=client_info or {},
            capabilities=capabilities or {}
        )
        
        with self.lock:
            self.sessions[session_id] = session
            self.logger.info(f"Created session {session_id[:8]}... for client")
            
        # Trigger cleanup if needed
        self._cleanup_expired_sessions()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object if found and not expired, None otherwise
        """
        if not session_id:
            return None
            
        with self.lock:
            session = self.sessions.get(session_id)
            
            if not session:
                self.logger.debug(f"Session {session_id[:8]}... not found")
                return None
                
            if session.is_expired(self.session_timeout):
                self.logger.info(f"Session {session_id[:8]}... expired, removing")
                del self.sessions[session_id]
                return None
                
            # Update access time
            session.update_access_time()
            self.logger.debug(f"Retrieved session {session_id[:8]}...")
            return session
    
    def validate_session(self, session_id: str) -> bool:
        """Validate if a session ID is valid and not expired.
        
        Args:
            session_id: Session identifier to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        session = self.get_session(session_id)
        return session is not None
    
    def update_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Update session context data.
        
        Args:
            session_id: Session identifier
            context: Context data to update
            
        Returns:
            True if update was successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
            
        with self.lock:
            session.context.update(context)
            session.update_access_time()
            self.logger.debug(f"Updated context for session {session_id[:8]}...")
            
        return True
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session by ID.
        
        Args:
            session_id: Session identifier to remove
            
        Returns:
            True if session was removed, False if not found
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.logger.info(f"Removed session {session_id[:8]}...")
                return True
                
        self.logger.debug(f"Session {session_id[:8]}... not found for removal")
        return False
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions (internal method)."""
        current_time = time.time()
        
        # Only run cleanup if enough time has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
            
        with self.lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if session.is_expired(self.session_timeout)
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                self.logger.info(f"Cleaned up expired session {session_id[:8]}...")
                
            self.last_cleanup = current_time
            
            if expired_sessions:
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def cleanup_all_sessions(self) -> int:
        """Force cleanup of all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        with self.lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if session.is_expired(self.session_timeout)
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                
            self.last_cleanup = time.time()
            self.logger.info(f"Force cleaned up {len(expired_sessions)} expired sessions")
            
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """Get the current number of active sessions."""
        with self.lock:
            return len(self.sessions)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active sessions (for debugging/monitoring).
        
        Returns:
            Dictionary of session IDs to session data
        """
        with self.lock:
            return {
                session_id: session.to_dict()
                for session_id, session in self.sessions.items()
                if not session.is_expired(self.session_timeout)
            }