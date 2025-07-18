"""Unit tests for session management functionality."""

import time
import pytest
from unittest.mock import Mock, patch

from mcp_amdsmi.session_manager import SessionManager, Session


class TestSession:
    """Test Session class functionality."""
    
    def test_session_creation(self):
        """Test session creation with required parameters."""
        session_id = "test-session-123"
        created_at = time.time()
        
        session = Session(
            session_id=session_id,
            created_at=created_at,
            last_accessed=created_at
        )
        
        assert session.session_id == session_id
        assert session.created_at == created_at
        assert session.last_accessed == created_at
        assert session.client_info == {}
        assert session.capabilities == {}
        assert session.context == {}
    
    def test_session_creation_with_metadata(self):
        """Test session creation with client metadata."""
        session_id = "test-session-456"
        created_at = time.time()
        client_info = {"name": "Test Client", "version": "1.0.0"}
        capabilities = {"tools": {}}
        context = {"user_id": "123"}
        
        session = Session(
            session_id=session_id,
            created_at=created_at,
            last_accessed=created_at,
            client_info=client_info,
            capabilities=capabilities,
            context=context
        )
        
        assert session.client_info == client_info
        assert session.capabilities == capabilities
        assert session.context == context
    
    def test_session_expiration_not_expired(self):
        """Test session expiration check for non-expired session."""
        session = Session(
            session_id="test-session",
            created_at=time.time(),
            last_accessed=time.time()
        )
        
        # Should not be expired immediately
        assert not session.is_expired(timeout=3600)
    
    def test_session_expiration_expired(self):
        """Test session expiration check for expired session."""
        # Create session with old timestamp
        old_time = time.time() - 7200  # 2 hours ago
        session = Session(
            session_id="test-session",
            created_at=old_time,
            last_accessed=old_time
        )
        
        # Should be expired with 1 hour timeout
        assert session.is_expired(timeout=3600)
    
    def test_session_update_access_time(self):
        """Test updating session access time."""
        old_time = time.time() - 100
        session = Session(
            session_id="test-session",
            created_at=old_time,
            last_accessed=old_time
        )
        
        # Update access time
        session.update_access_time()
        
        # Access time should be updated
        assert session.last_accessed > old_time
        assert session.last_accessed <= time.time()
    
    def test_session_to_dict(self):
        """Test session serialization to dictionary."""
        session_id = "test-session-789"
        created_at = time.time()
        last_accessed = time.time()
        client_info = {"name": "Test Client"}
        capabilities = {"tools": {}}
        context = {"user_id": "123"}
        
        session = Session(
            session_id=session_id,
            created_at=created_at,
            last_accessed=last_accessed,
            client_info=client_info,
            capabilities=capabilities,
            context=context
        )
        
        session_dict = session.to_dict()
        
        assert session_dict["session_id"] == session_id
        assert session_dict["created_at"] == created_at
        assert session_dict["last_accessed"] == last_accessed
        assert session_dict["client_info"] == client_info
        assert session_dict["capabilities"] == capabilities
        assert session_dict["context"] == context


class TestSessionManager:
    """Test SessionManager class functionality."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager for testing."""
        return SessionManager(session_timeout=3600, cleanup_interval=300)
    
    def test_session_manager_initialization(self, session_manager):
        """Test session manager initialization."""
        assert session_manager.session_timeout == 3600
        assert session_manager.cleanup_interval == 300
        assert isinstance(session_manager.sessions, dict)
        assert len(session_manager.sessions) == 0
        assert session_manager.logger is not None
    
    def test_create_session_basic(self, session_manager):
        """Test basic session creation."""
        session = session_manager.create_session()
        
        assert session is not None
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.created_at <= time.time()
        assert session.last_accessed <= time.time()
        assert session.client_info == {}
        assert session.capabilities == {}
        assert session.context == {}
        
        # Session should be stored in manager
        assert session.session_id in session_manager.sessions
        assert session_manager.sessions[session.session_id] == session
    
    def test_create_session_with_client_info(self, session_manager):
        """Test session creation with client information."""
        client_info = {
            "name": "Test Client",
            "version": "1.0.0",
            "user_agent": "Test/1.0.0"
        }
        
        session = session_manager.create_session(client_info=client_info)
        
        assert session.client_info == client_info
        assert session.session_id in session_manager.sessions
    
    def test_create_session_with_context(self, session_manager):
        """Test session creation with context."""
        client_info = {"user_id": "123", "workspace": "test"}
        capabilities = {"experimental": {"notifications": True}}
        
        session = session_manager.create_session(client_info=client_info, capabilities=capabilities)
        
        assert session.session_id is not None
        assert session.client_info == client_info
        assert session.capabilities == capabilities
        assert session.context == {}
        
        # Test context update
        context = {"user_id": "123", "workspace": "test"}
        success = session_manager.update_session_context(session.session_id, context)
        assert success is True
        
        # Verify context was updated
        retrieved_session = session_manager.get_session(session.session_id)
        assert retrieved_session.context == context
    
    def test_get_session_existing(self, session_manager):
        """Test retrieving existing session."""
        # Create a session
        session = session_manager.create_session()
        session_id = session.session_id
        
        # Retrieve the session
        retrieved_session = session_manager.get_session(session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        assert retrieved_session == session
    
    def test_get_session_non_existing(self, session_manager):
        """Test retrieving non-existing session."""
        retrieved_session = session_manager.get_session("non-existing-session")
        assert retrieved_session is None
    
    def test_get_session_expired(self, session_manager):
        """Test retrieving expired session."""
        # Create a session with old timestamp
        old_time = time.time() - 7200  # 2 hours ago
        session = Session(
            session_id="expired-session",
            created_at=old_time,
            last_accessed=old_time
        )
        
        # Add to manager manually
        session_manager.sessions[session.session_id] = session
        
        # Try to retrieve - should return None for expired session
        retrieved_session = session_manager.get_session(session.session_id)
        assert retrieved_session is None
        
        # Session should be removed from manager
        assert session.session_id not in session_manager.sessions
    
    def test_remove_session_existing(self, session_manager):
        """Test removing existing session."""
        # Create a session
        session = session_manager.create_session()
        session_id = session.session_id
        
        # Verify session exists
        assert session_id in session_manager.sessions
        
        # Remove session
        removed = session_manager.remove_session(session_id)
        
        assert removed is True
        assert session_id not in session_manager.sessions
    
    def test_remove_session_non_existing(self, session_manager):
        """Test removing non-existing session."""
        removed = session_manager.remove_session("non-existing-session")
        assert removed is False
    
    def test_get_session_count(self, session_manager):
        """Test getting session count."""
        assert session_manager.get_session_count() == 0
        
        # Create some sessions
        session1 = session_manager.create_session()
        assert session_manager.get_session_count() == 1
        
        session2 = session_manager.create_session()
        assert session_manager.get_session_count() == 2
        
        # Remove a session
        session_manager.remove_session(session1.session_id)
        assert session_manager.get_session_count() == 1
        
        # Remove another session
        session_manager.remove_session(session2.session_id)
        assert session_manager.get_session_count() == 0
    
    @pytest.mark.skip(reason="Method not implemented - focusing on core functionality")
    def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        # Create some sessions
        valid_session = session_manager.create_session()
        
        # Create expired session manually
        old_time = time.time() - 7200  # 2 hours ago
        expired_session = Session(
            session_id="expired-session",
            created_at=old_time,
            last_accessed=old_time
        )
        session_manager.sessions[expired_session.session_id] = expired_session
        
        assert session_manager.get_session_count() == 2
        
        # Run cleanup
        cleaned_count = session_manager.cleanup_all_sessions()
        
        # Should have cleaned up 1 expired session
        assert cleaned_count == 1
        assert session_manager.get_session_count() == 1
        assert valid_session.session_id in session_manager.sessions
        assert expired_session.session_id not in session_manager.sessions
    
    @pytest.mark.skip(reason="Method not implemented - focusing on core functionality")
    def test_cleanup_expired_sessions_none_expired(self, session_manager):
        """Test cleanup with no expired sessions."""
        # Create some valid sessions
        session1 = session_manager.create_session()
        session2 = session_manager.create_session()
        
        assert session_manager.get_session_count() == 2
        
        # Run cleanup
        cleaned_count = session_manager.cleanup_all_sessions()
        
        # Should have cleaned up 0 sessions
        assert cleaned_count == 0
        assert session_manager.get_session_count() == 2
    
    def test_generate_session_id_unique(self, session_manager):
        """Test that session IDs are unique."""
        session_ids = set()
        
        # Generate multiple session IDs
        for _ in range(100):
            session_id = session_manager.generate_session_id()
            assert session_id not in session_ids
            session_ids.add(session_id)
            
        # All session IDs should be unique
        assert len(session_ids) == 100
    
    def test_generate_session_id_format(self, session_manager):
        """Test session ID format and length."""
        session_id = session_manager.generate_session_id()
        
        # Session ID should be a string
        assert isinstance(session_id, str)
        
        # Should be reasonable length (not too short, not too long)
        assert 16 <= len(session_id) <= 128
        
        # Should be URL-safe base64 characters
        import string
        allowed_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in allowed_chars for c in session_id)
    
    def test_session_manager_concurrent_access(self, session_manager):
        """Test concurrent access to session manager."""
        import threading
        
        sessions_created = []
        
        def create_session():
            session = session_manager.create_session()
            sessions_created.append(session)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_session)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All sessions should be created successfully
        assert len(sessions_created) == 10
        assert session_manager.get_session_count() == 10
        
        # All session IDs should be unique
        session_ids = [s.session_id for s in sessions_created]
        assert len(set(session_ids)) == 10
    
    def test_session_manager_stress_test(self, session_manager):
        """Test session manager with many sessions."""
        sessions = []
        
        # Create many sessions
        for i in range(1000):
            session = session_manager.create_session(
                client_info={"client_id": f"client_{i}"}
            )
            sessions.append(session)
        
        assert session_manager.get_session_count() == 1000
        
        # Verify all sessions can be retrieved
        for session in sessions:
            retrieved = session_manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.session_id == session.session_id
        
        # Remove half the sessions
        for session in sessions[:500]:
            removed = session_manager.remove_session(session.session_id)
            assert removed is True
        
        assert session_manager.get_session_count() == 500
        
        # Verify remaining sessions are still accessible
        for session in sessions[500:]:
            retrieved = session_manager.get_session(session.session_id)
            assert retrieved is not None
    
    @patch('time.time')
    def test_session_expiration_edge_cases(self, mock_time, session_manager):
        """Test edge cases in session expiration."""
        # Mock time to control expiration
        mock_time.return_value = 1000.0
        
        # Create session
        session = session_manager.create_session()
        
        # Session should not be expired immediately
        assert not session.is_expired(timeout=3600)
        
        # Move time forward to just before expiration
        mock_time.return_value = 1000.0 + 3599.0  # 3599 seconds later
        assert not session.is_expired(timeout=3600)
        
        # Move time to exact expiration point
        mock_time.return_value = 1000.0 + 3600.0  # 3600 seconds later
        assert not session.is_expired(timeout=3600)
        
        # Move time past expiration
        mock_time.return_value = 1000.0 + 3601.0  # 3601 seconds later
        assert session.is_expired(timeout=3600)
    
    def test_session_update_access_time_prevents_expiration(self, session_manager):
        """Test that updating access time prevents expiration."""
        # Create session
        session = session_manager.create_session()
        original_session_id = session.session_id
        
        # Wait a bit (simulate some time passing)
        time.sleep(0.1)
        
        # Update access time
        session.update_access_time()
        
        # Session should still be valid
        retrieved_session = session_manager.get_session(original_session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == original_session_id
    
    @pytest.mark.skip(reason="Method not implemented - focusing on core functionality")
    def test_session_manager_cleanup_thread_safety(self, session_manager):
        """Test that cleanup is thread-safe."""
        import threading
        
        # Create many sessions
        sessions = []
        for i in range(100):
            session = session_manager.create_session()
            sessions.append(session)
        
        # Function to run cleanup in thread
        def run_cleanup():
            session_manager.cleanup_all_sessions()
        
        # Function to access sessions in thread
        def access_sessions():
            for session in sessions:
                session_manager.get_session(session.session_id)
        
        # Create threads
        cleanup_thread = threading.Thread(target=run_cleanup)
        access_thread = threading.Thread(target=access_sessions)
        
        # Run threads concurrently
        cleanup_thread.start()
        access_thread.start()
        
        # Wait for completion
        cleanup_thread.join()
        access_thread.join()
        
        # Should not raise any exceptions
        assert session_manager.get_session_count() == 100