"""Natural language command interpreter for AI Memory.

Detects user intents and converts natural language to system commands.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    """Detected user intents."""
    REMEMBER = "remember"  # "remember that I love Python"
    RECALL = "recall"  # "what did I tell you about cats?"
    FORGET = "forget"  # "forget about my old job"
    SEARCH = "search"  # "search for python notes"
    LIST = "list"  # "what do you know about me?"
    UPDATE = "update"  # "actually I prefer Ruby now"
    CHAT = "chat"  # Normal conversation
    HELP = "help"  # "what can you do?"


class CommandInterpreter:
    """Interprets natural language as system commands."""
    
    def __init__(self):
        """Initialize command interpreter with pattern matching."""
        
        # Intent detection patterns
        self.intent_patterns = {
            UserIntent.REMEMBER: [
                r"remember (that )?(.+)",
                r"store (this:|that)?(.+)",
                r"save (this:|that)?(.+)",
                r"keep in mind (that )?(.+)",
                r"note (that )?(.+)",
                r"don't forget (that )?(.+)",
                r"I (want you to )?(know|remember) (that )?(.+)",
            ],
            UserIntent.RECALL: [
                r"what (did I|have I) (tell|told|say|said) you about (.+)",
                r"(do you remember|recall) (.+)",
                r"what do you know about (.+)",
                r"tell me (about|what you know about) (.+)",
                r"what('s| is) my (.+)",
                r"remind me (about|of) (.+)",
            ],
            UserIntent.FORGET: [
                r"forget (about |that )?(.+)",
                r"delete (.+)",
                r"remove (.+) from (your )?memory",
                r"don't remember (.+)",
                r"erase (.+)",
            ],
            UserIntent.SEARCH: [
                r"search (for |your memory for )?(.+)",
                r"find (.+) in (your )?memory",
                r"look up (.+)",
            ],
            UserIntent.LIST: [
                r"what do you (know|remember) about me",
                r"list (all |everything )?you know",
                r"show me (all |everything )?you('ve| have) (stored|remembered)",
                r"what have I told you",
            ],
            UserIntent.HELP: [
                r"what can you do",
                r"help( me)?$",
                r"how (do I |can I )?use (this|you)",
                r"what (commands|features) (do you have|are available)",
            ],
        }
    
    def detect_intent(self, user_input: str) -> Tuple[UserIntent, Dict[str, Any]]:
        """Detect user intent from natural language.
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Tuple of (intent, extracted_params)
        """
        normalized = user_input.lower().strip()
        
        # Try each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.match(pattern, normalized, re.IGNORECASE)
                if match:
                    # Extract parameters based on intent
                    params = self._extract_params(intent, match, user_input)
                    logger.info(f"Detected intent: {intent} with params: {params}")
                    return intent, params
        
        # Default: normal chat
        return UserIntent.CHAT, {"message": user_input}
    
    def _extract_params(self, intent: UserIntent, match: re.Match, original_input: str) -> Dict[str, Any]:
        """Extract parameters from regex match based on intent."""
        
        groups = match.groups()
        
        if intent == UserIntent.REMEMBER:
            # Extract what to remember
            content = groups[-1].strip() if groups else original_input
            
            # Detect type from content
            content_type = self._infer_type(content)
            tags = self._extract_tags(content)
            
            return {
                "content": content,
                "type": content_type,
                "tags": tags,
                "source": "chat_command"
            }
        
        elif intent == UserIntent.RECALL:
            # Extract what to recall
            query = groups[-1].strip() if groups else original_input
            return {
                "query": query,
                "limit": 5
            }
        
        elif intent == UserIntent.FORGET:
            # Extract what to forget
            content = groups[-1].strip() if groups else original_input
            return {
                "query": content
            }
        
        elif intent == UserIntent.SEARCH:
            # Extract search query
            query = groups[-1].strip() if groups else original_input
            return {
                "query": query,
                "limit": 10
            }
        
        elif intent == UserIntent.LIST:
            return {
                "limit": 20
            }
        
        else:
            return {}
    
    def _infer_type(self, content: str) -> str:
        """Infer content type from text."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["prefer", "like", "love", "hate", "favorite"]):
            return "preference"
        elif any(word in content_lower for word in ["work", "job", "career", "company"]):
            return "work"
        elif any(word in content_lower for word in ["my name is", "I am", "I'm a", "I have"]):
            return "personal"
        else:
            return "note"
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract potential tags from content."""
        tags = []
        
        # Simple keyword extraction
        keywords = {
            "python": ["python", "py", "django", "flask"],
            "work": ["work", "job", "career", "office"],
            "personal": ["family", "friend", "pet", "cat", "dog"],
            "tech": ["programming", "coding", "software", "developer"],
            "preference": ["prefer", "like", "love", "favorite"],
        }
        
        content_lower = content.lower()
        for tag, words in keywords.items():
            if any(word in content_lower for word in words):
                tags.append(tag)
        
        # Add from chat conversation
        tags.append("conversation")
        
        return tags[:5]  # Limit to 5 tags
    
    async def execute_intent(
        self, 
        intent: UserIntent, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the detected intent.
        
        Args:
            intent: Detected user intent
            params: Extracted parameters
            
        Returns:
            Result dictionary with status and message
        """
        try:
            if intent == UserIntent.REMEMBER:
                return await self._execute_remember(params)
            
            elif intent == UserIntent.RECALL:
                return await self._execute_recall(params)
            
            elif intent == UserIntent.FORGET:
                return await self._execute_forget(params)
            
            elif intent == UserIntent.SEARCH:
                return await self._execute_search(params)
            
            elif intent == UserIntent.LIST:
                return await self._execute_list(params)
            
            elif intent == UserIntent.HELP:
                return await self._execute_help(params)
            
            else:
                # Normal chat - no command execution
                return {
                    "intent": "chat",
                    "execute_command": False,
                    "message": None
                }
                
        except Exception as e:
            logger.error(f"Intent execution failed: {e}")
            return {
                "intent": str(intent),
                "execute_command": False,
                "error": str(e),
                "message": f"I tried to {intent} but encountered an error: {str(e)}"
            }
    
    async def _execute_remember(self, params: Dict) -> Dict:
        """Execute REMEMBER intent - store in memory."""
        from ..services import vault_service
        
        try:
            entry = vault_service.save_context(
                content=params["content"],
                context_type=params["type"],
                tags=params.get("tags", []),
                metadata={"source": params.get("source", "chat_command")},
            )
            
            return {
                "intent": "remember",
                "execute_command": True,
                "success": True,
                "entry_id": entry.id,
                "message": f"✅ I'll remember that: \"{params['content'][:60]}{'...' if len(params['content']) > 60 else ''}\""
            }
        except Exception as e:
            logger.error(f"Remember execution failed: {e}")
            return {
                "intent": "remember",
                "execute_command": True,
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to remember: {str(e)}"
            }
    
    async def _execute_recall(self, params: Dict) -> Dict:
        """Execute RECALL intent - search memory."""
        from ..services import vault_service
        
        try:
            results, total = vault_service.search_context(
                query=params["query"],
                limit=params.get("limit", 5)
            )
            
            if results:
                memories = [entry.content for entry in results]
                return {
                    "intent": "recall",
                    "execute_command": True,
                    "success": True,
                    "memories": memories,
                    "count": len(results),
                    "message": f"📚 I found {len(results)} memories about '{params['query']}':\n" + 
                              "\n".join([f"  • {m[:80]}..." if len(m) > 80 else f"  • {m}" for m in memories[:3]])
                }
            else:
                return {
                    "intent": "recall",
                    "execute_command": True,
                    "success": False,
                    "message": f"🤔 I don't have any memories about '{params['query']}' yet."
                }
        except Exception as e:
            logger.error(f"Recall execution failed: {e}")
            return {
                "intent": "recall",
                "execute_command": True,
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to recall: {str(e)}"
            }
    
    async def _execute_forget(self, params: Dict) -> Dict:
        """Execute FORGET intent - delete from memory."""
        from ..services import vault_service
        
        try:
            # Search for matching entries
            results, total = vault_service.search_context(
                query=params["query"],
                limit=5
            )
            
            if results:
                # Delete first match
                vault_service.delete_context(results[0].id)
                
                return {
                    "intent": "forget",
                    "execute_command": True,
                    "success": True,
                    "deleted_id": results[0].id,
                    "message": f"🗑️ I've forgotten about: \"{results[0].content[:60]}...\""
                }
            else:
                return {
                    "intent": "forget",
                    "execute_command": True,
                    "success": False,
                    "message": f"🤔 I couldn't find anything about '{params['query']}' to forget."
                }
        except Exception as e:
            logger.error(f"Forget execution failed: {e}")
            return {
                "intent": "forget",
                "execute_command": True,
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to forget: {str(e)}"
            }
    
    async def _execute_search(self, params: Dict) -> Dict:
        """Execute SEARCH intent - search memory."""
        # Same as recall
        return await self._execute_recall(params)
    
    async def _execute_list(self, params: Dict) -> Dict:
        """Execute LIST intent - list memories."""
        from ..services import vault_service
        
        try:
            results, total = vault_service.get_context(
                limit=params.get("limit", 20),
                order_by="created_at",
                order_desc=True
            )
            
            if results:
                summaries = [f"{entry.context_type}: {entry.content[:60]}..." 
                            if len(entry.content) > 60 
                            else f"{entry.context_type}: {entry.content}"
                            for entry in results[:10]]
                
                return {
                    "intent": "list",
                    "execute_command": True,
                    "success": True,
                    "total": total,
                    "showing": len(summaries),
                    "message": f"📋 I have {total} memories about you. Here are the most recent:\n" +
                              "\n".join([f"  {i+1}. {s}" for i, s in enumerate(summaries)])
                }
            else:
                return {
                    "intent": "list",
                    "execute_command": True,
                    "success": False,
                    "message": "📋 I don't have any memories about you yet. Tell me about yourself!"
                }
        except Exception as e:
            logger.error(f"List execution failed: {e}")
            return {
                "intent": "list",
                "execute_command": True,
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to list memories: {str(e)}"
            }
    
    async def _execute_help(self, params: Dict) -> Dict:
        """Execute HELP intent - show available commands."""
        help_text = """
🤖 AI Memory - What I Can Do:

💬 Natural Commands (just talk to me naturally):
   • "Remember that I love Python" - I'll store it
   • "What did I tell you about cats?" - I'll search my memory
   • "What do you know about me?" - I'll list everything
   • "Forget about my old job" - I'll delete it
   • "Search for Python notes" - I'll find them

📝 I automatically detect these intents and execute them!

🎯 Or use explicit commands:
   • ai-memory feed file.pdf - Upload documents
   • ai-memory recall "query" - Search memory
   • ai-memory context list - See all memories

💡 Tips:
   • I learn from our conversations automatically
   • I organize memories by importance (Cognitive Workspace)
   • I track relationships (Bob works at Acme)
   • I remember forever (unless you ask me to forget)
"""
        return {
            "intent": "help",
            "execute_command": True,
            "success": True,
            "message": help_text
        }
    
    def format_for_context(
        self, 
        user_input: str, 
        intent_result: Optional[Dict] = None
    ) -> str:
        """Format user input with command execution result for optimal AI context.
        
        Args:
            user_input: Original user input
            intent_result: Result from executing intent (if any)
            
        Returns:
            Optimally formatted prompt for AI
        """
        if not intent_result or not intent_result.get("execute_command"):
            # Normal chat - just return input
            return user_input
        
        # Command was executed - include result in context
        if intent_result.get("success"):
            # Successful command execution
            context_message = f"""
[SYSTEM ACTION EXECUTED]
User said: "{user_input}"
Action: {intent_result["intent"].upper()}
Result: {intent_result.get("message", "Success")}

[RESPOND NATURALLY]
Acknowledge the action was successful and respond helpfully to the user's request.
"""
        else:
            # Failed command execution
            context_message = f"""
[SYSTEM ACTION FAILED]
User said: "{user_input}"
Action: {intent_result["intent"].upper()}
Error: {intent_result.get("error", "Unknown error")}

[RESPOND NATURALLY]
Acknowledge the action failed and suggest alternatives.
"""
        
        return context_message


# Global interpreter instance
command_interpreter = CommandInterpreter()


async def process_user_input(user_input: str) -> Tuple[str, Dict[str, Any]]:
    """Process user input for natural language commands.
    
    Args:
        user_input: User's natural language input
        
    Returns:
        Tuple of (formatted_context, intent_result)
        
    Example:
        >>> formatted, result = await process_user_input("remember that I love Python")
        >>> print(result["message"])
        ✅ I'll remember that: "I love Python"
    """
    # Detect intent
    intent, params = command_interpreter.detect_intent(user_input)
    
    # Execute if it's a command
    if intent != UserIntent.CHAT:
        result = await command_interpreter.execute_intent(intent, params)
        
        # Format for optimal AI context
        formatted = command_interpreter.format_for_context(user_input, result)
        
        return formatted, result
    else:
        # Normal chat - no command
        return user_input, {"intent": "chat", "execute_command": False}

