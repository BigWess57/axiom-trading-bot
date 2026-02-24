from typing import Dict, Optional
from ..auth.auth_manager import AuthManager

class AuthMixin:
    """Authentication related methods for AxiomTradeClient"""
    
    # Type hinting for mixin dependencies
    auth_manager: AuthManager
    
    @property
    def access_token(self) -> Optional[str]:
        """Get current access token"""
        return self.auth_manager.tokens.access_token if self.auth_manager.tokens else None
    
    @property
    def refresh_token(self) -> Optional[str]:
        """Get current refresh token"""
        return self.auth_manager.tokens.refresh_token if self.auth_manager.tokens else None
    
    def login(self, email: str = None, password: str = None) -> Dict:
        """
        Login with username and password using the enhanced auth flow
        
        Args:
            email: Email address (optional if provided in constructor)
            password: Password (optional if provided in constructor)
            
        Returns:
            Dict: Login result with token information
        """
        # Use provided credentials or fall back to constructor values
        email = email or self.auth_manager.username
        password = password or self.auth_manager.password
        
        if not email or not password:
            raise ValueError("Email and password are required for login")
        
        # Update auth manager credentials
        self.auth_manager.username = email
        self.auth_manager.password = password
        
        # Perform authentication
        success = self.auth_manager.authenticate()
        
        if success and self.auth_manager.tokens:
            return {
                'success': True,
                'access_token': self.auth_manager.tokens.access_token,
                'refresh_token': self.auth_manager.tokens.refresh_token,
                'expires_at': self.auth_manager.tokens.expires_at,
                'message': 'Login successful'
            }
        else:
            return {
                'success': False,
                'message': 'Login failed'
            }
    
    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        """
        Set authentication tokens directly
        
        Args:
            access_token: The access token
            refresh_token: The refresh token
        """
        self.auth_manager._set_tokens(access_token, refresh_token)
    
    def get_tokens(self) -> Dict[str, Optional[str]]:
        """
        Get current tokens
        """
        tokens = self.auth_manager.tokens
        return {
            'access_token': tokens.access_token if tokens else None,
            'refresh_token': tokens.refresh_token if tokens else None,
            'expires_at': tokens.expires_at if tokens else None,
            'is_expired': tokens.is_expired if tokens else True
        }
    
    def is_authenticated(self) -> bool:
        """
        Check if the client has valid authentication tokens
        """
        return self.auth_manager.is_authenticated()
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using stored refresh token
        
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        return self.auth_manager.refresh_tokens()
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure the client has valid authentication tokens
        Automatically refreshes or re-authenticates as needed
        
        Returns:
            bool: True if valid authentication available, False otherwise
        """
        return self.auth_manager.ensure_valid_authentication()
    
    def logout(self) -> None:
        """Clear all authentication data including saved tokens"""
        self.auth_manager.logout()
    
    def clear_saved_tokens(self) -> bool:
        """Clear saved tokens from secure storage"""
        return self.auth_manager.clear_saved_tokens()
    
    def has_saved_tokens(self) -> bool:
        """Check if saved tokens exist in secure storage"""
        return self.auth_manager.has_saved_tokens()
    
    def get_token_info_detailed(self) -> Dict:
        """Get detailed information about current tokens"""
        return self.auth_manager.get_token_info()
