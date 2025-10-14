"""Token counting service with support for multiple tokenizer types."""

import logging
from typing import Optional, Union, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class TokenCounter:
    """Service for accurate token counting across different model types."""

    def __init__(self):
        """Initialize token counter with lazy-loaded tokenizers."""
        self._tokenizers = {}
        self._tiktoken_available = self._check_tiktoken()
        self._transformers_available = self._check_transformers()

    def _check_tiktoken(self) -> bool:
        """Check if tiktoken is available (for GPT models)."""
        try:
            import tiktoken
            return True
        except ImportError:
            logger.warning("tiktoken not installed - GPT token counting will use estimation")
            return False

    def _check_transformers(self) -> bool:
        """Check if transformers is available (for other models)."""
        try:
            from transformers import AutoTokenizer
            return True
        except ImportError:
            logger.warning("transformers not installed - will use character estimation")
            return False

    @lru_cache(maxsize=10)
    def _get_tokenizer(self, tokenizer_type: str):
        """
        Get or create tokenizer instance (cached).

        Args:
            tokenizer_type: Type of tokenizer (llama, mistral, gpt, gemma)

        Returns:
            Tokenizer instance or None if unavailable
        """
        if tokenizer_type in self._tokenizers:
            return self._tokenizers[tokenizer_type]

        try:
            if tokenizer_type == "gpt" and self._tiktoken_available:
                import tiktoken
                tokenizer = tiktoken.get_encoding("cl100k_base")
                self._tokenizers[tokenizer_type] = tokenizer
                logger.info(f"Loaded tiktoken tokenizer for {tokenizer_type}")
                return tokenizer

            elif self._transformers_available:
                from transformers import AutoTokenizer

                # Map tokenizer types to HuggingFace model IDs
                model_map = {
                    "llama": "meta-llama/Llama-2-7b-hf",
                    "mistral": "mistralai/Mistral-7B-v0.1",
                    "gemma": "google/gemma-7b",
                    "phi": "microsoft/phi-2",
                }

                model_id = model_map.get(tokenizer_type, model_map["llama"])
                tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    use_fast=True,
                    trust_remote_code=False
                )
                self._tokenizers[tokenizer_type] = tokenizer
                logger.info(f"Loaded HuggingFace tokenizer for {tokenizer_type}")
                return tokenizer

        except Exception as e:
            logger.warning(f"Failed to load tokenizer for {tokenizer_type}: {e}")

        return None

    def count_tokens(
        self,
        text: Union[str, List[str]],
        tokenizer_type: str = "llama",
        use_estimation: bool = False
    ) -> int:
        """
        Count tokens in text using appropriate tokenizer.

        Args:
            text: Text string or list of strings to count
            tokenizer_type: Type of tokenizer to use
            use_estimation: Fall back to character estimation if True

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Convert list to single string
        if isinstance(text, list):
            text = "\n\n".join(text)

        # Try actual tokenizer first
        if not use_estimation:
            tokenizer = self._get_tokenizer(tokenizer_type)

            if tokenizer:
                try:
                    if tokenizer_type == "gpt":
                        # tiktoken
                        return len(tokenizer.encode(text))
                    else:
                        # HuggingFace
                        return len(tokenizer.encode(text, add_special_tokens=True))
                except Exception as e:
                    logger.warning(f"Token counting failed, using estimation: {e}")

        # Fallback to character-based estimation
        return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate tokens using character count.

        Rule of thumb:
        - English: ~4 characters per token
        - Code: ~3 characters per token
        - Average: ~3.5 characters per token

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        char_count = len(text)

        # Adjust for whitespace (more whitespace = more tokens)
        word_count = len(text.split())
        whitespace_ratio = (char_count - word_count) / char_count if char_count > 0 else 0

        # Base estimation
        if whitespace_ratio < 0.15:  # Dense text (like code)
            tokens = char_count / 3.0
        elif whitespace_ratio > 0.25:  # Sparse text (lots of spaces)
            tokens = char_count / 4.5
        else:  # Normal text
            tokens = char_count / 3.5

        return int(tokens) + 1  # Always round up

    def count_tokens_batch(
        self,
        texts: List[str],
        tokenizer_type: str = "llama"
    ) -> List[int]:
        """
        Count tokens for multiple texts efficiently.

        Args:
            texts: List of text strings
            tokenizer_type: Type of tokenizer to use

        Returns:
            List of token counts
        """
        return [self.count_tokens(text, tokenizer_type) for text in texts]

    def fits_in_window(
        self,
        text: str,
        max_tokens: int,
        tokenizer_type: str = "llama"
    ) -> bool:
        """
        Check if text fits within token window.

        Args:
            text: Text to check
            max_tokens: Maximum token limit
            tokenizer_type: Type of tokenizer

        Returns:
            True if text fits, False otherwise
        """
        token_count = self.count_tokens(text, tokenizer_type)
        return token_count <= max_tokens

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        tokenizer_type: str = "llama",
        from_end: bool = False
    ) -> str:
        """
        Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens
            tokenizer_type: Type of tokenizer
            from_end: If True, truncate from end; if False, from beginning

        Returns:
            Truncated text
        """
        current_tokens = self.count_tokens(text, tokenizer_type)

        if current_tokens <= max_tokens:
            return text

        # Estimate characters to keep
        chars_per_token = len(text) / current_tokens
        target_chars = int(max_tokens * chars_per_token * 0.95)  # 95% to be safe

        if from_end:
            truncated = text[-target_chars:]
            # Try to start at word boundary
            first_space = truncated.find(' ')
            if first_space > 0 and first_space < 50:
                truncated = truncated[first_space + 1:]
        else:
            truncated = text[:target_chars]
            # Try to end at word boundary
            last_space = truncated.rfind(' ')
            if last_space > target_chars - 50:
                truncated = truncated[:last_space]

        # Verify we're under the limit
        if self.count_tokens(truncated, tokenizer_type) > max_tokens:
            # Recursively truncate more aggressively
            return self.truncate_to_tokens(truncated, max_tokens, tokenizer_type, from_end)

        return truncated

    def get_token_statistics(self, text: str, tokenizer_type: str = "llama") -> dict:
        """
        Get detailed token statistics for text.

        Args:
            text: Text to analyze
            tokenizer_type: Type of tokenizer

        Returns:
            Dictionary with token statistics
        """
        tokens = self.count_tokens(text, tokenizer_type)
        chars = len(text)
        words = len(text.split())

        return {
            "tokens": tokens,
            "characters": chars,
            "words": words,
            "chars_per_token": round(chars / tokens, 2) if tokens > 0 else 0,
            "tokens_per_word": round(tokens / words, 2) if words > 0 else 0,
            "tokenizer_type": tokenizer_type,
        }


# Global token counter instance
token_counter = TokenCounter()
