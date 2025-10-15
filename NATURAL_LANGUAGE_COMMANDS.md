# 🗣️ Natural Language Commands - Talk Naturally, AI Understands

## 🎯 **What This Does**

Instead of typing CLI commands, **just talk naturally** and the system understands!

---

## 💬 **Examples**

### **Before (Old Way - Manual Commands):**
```bash
$ ai-memory context add "I love Python programming"
$ ai-memory context add "I have two cats named Luna and Pixel"
$ ai-memory recall "cats"
```

### **After (New Way - Natural Language):**
```bash
$ ai-memory chat

You: Remember that I love Python programming
AI: ✅ I'll remember that you love Python programming!
    [Automatically saved to database]

You: I have two cats named Luna and Pixel
AI: ✅ I'll remember that you have two cats named Luna and Pixel!
    [Automatically detected as memory and saved]

You: What did I tell you about cats?
AI: 📚 I found 1 memory about 'cats':
    • You have two cats named Luna and Pixel
    [Automatically searched and recalled]
```

**You just talk naturally - AI detects commands automatically!**

---

## 🤖 **Natural Language Commands Supported**

### **1. REMEMBER (Store Information)**

**Natural Ways to Say It:**
```
"Remember that I love Python"
"Store this: I drive a Tesla"
"Save that I work at Google"
"Keep in mind that I'm allergic to peanuts"
"Note that I prefer email over Slack"
"Don't forget that my birthday is March 15"
"I want you to know I'm a software engineer"
```

**What Happens:**
- ✅ System detects "remember" intent
- ✅ Extracts content: "I love Python"
- ✅ Infers type: "preference"
- ✅ Adds tags automatically
- ✅ Saves to database
- ✅ AI responds: "I'll remember that..."

---

### **2. RECALL (Search Memory)**

**Natural Ways to Say It:**
```
"What did I tell you about cats?"
"Do you remember my job?"
"What do you know about Python?"
"Tell me about my preferences"
"What's my car?"
"Remind me about my meeting notes"
```

**What Happens:**
- ✅ System detects "recall" intent
- ✅ Extracts query: "cats", "job", "Python", etc.
- ✅ Searches database
- ✅ Returns top 5 results
- ✅ AI responds with findings

---

### **3. FORGET (Delete Information)**

**Natural Ways to Say It:**
```
"Forget about my old job"
"Delete my Tesla info"
"Remove my Python preference from memory"
"Don't remember that anymore"
"Erase my allergy info"
```

**What Happens:**
- ✅ System detects "forget" intent
- ✅ Searches for matching memory
- ✅ Deletes it
- ✅ AI confirms deletion

---

### **4. SEARCH (Find Specific Info)**

**Natural Ways to Say It:**
```
"Search for Python notes"
"Find cats in your memory"
"Look up my work history"
```

**What Happens:**
- ✅ System detects "search" intent
- ✅ Performs semantic search
- ✅ Returns results
- ✅ AI displays findings

---

### **5. LIST (Show Everything)**

**Natural Ways to Say It:**
```
"What do you know about me?"
"List everything you remember"
"Show me all you've stored"
"What have I told you?"
```

**What Happens:**
- ✅ System detects "list" intent
- ✅ Retrieves recent memories
- ✅ Shows top 10
- ✅ AI summarizes

---

### **6. HELP (Show Capabilities)**

**Natural Ways to Say It:**
```
"What can you do?"
"Help"
"How do I use this?"
"What commands are available?"
```

**What Happens:**
- ✅ System shows available commands
- ✅ Explains natural language syntax
- ✅ Gives examples

---

## 🔄 **How It Works (Technical)**

### **Step-by-Step Flow:**

```
User types: "Remember that I love Python"
     ↓
┌──────────────────────────────────────┐
│  COMMAND INTERPRETER                 │
│  • Analyzes text                     │
│  • Matches pattern: "remember that"  │
│  • Detected intent: REMEMBER         │
│  • Extract params:                   │
│    - content: "I love Python"        │
│    - type: "preference" (inferred)   │
│    - tags: ["python", "preference"]  │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  EXECUTE COMMAND                     │
│  • Call vault_service.save_context() │
│  • Store in database                 │
│  • Return success message            │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  FORMAT FOR AI                       │
│  Build optimal prompt:               │
│                                      │
│  [SYSTEM ACTION EXECUTED]            │
│  User: "Remember that I love Python" │
│  Action: REMEMBER                    │
│  Result: ✅ Saved                    │
│                                      │
│  [RESPOND NATURALLY]                 │
│  Acknowledge success to user         │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  AI MODEL                            │
│  Sees formatted prompt                │
│  Generates: "I'll remember that you  │
│             love Python!"             │
└──────────────────────────────────────┘
```

---

## 🎨 **Intent Detection (Pattern Matching)**

### **Remember Intent:**
```python
patterns = [
    r"remember (that )?(.+)",
    r"store (this:|that)?(.+)",
    r"save (this:|that)?(.+)",
    r"don't forget (that )?(.+)",
]

user_input = "remember that I love Python"
match = re.match("remember (that )?(.+)", user_input)
# Extracts: "I love Python"
```

### **Recall Intent:**
```python
patterns = [
    r"what (did I|have I) (tell|told|say|said) you about (.+)",
    r"what do you know about (.+)",
    r"what('s| is) my (.+)",
]

user_input = "what did I tell you about cats?"
match = re.match("what (did I|have I) (tell|told|say|said) you about (.+)", user_input)
# Extracts query: "cats"
```

---

## 💡 **Type Inference**

The system automatically infers content type from context:

```python
"I love Python" → type: "preference" (contains "love")
"I work at Google" → type: "work" (contains "work")
"My name is Alice" → type: "personal" (contains "my name is")
"Meeting notes..." → type: "note" (default)
```

**Tags are also auto-generated:**
```python
"I love Python" → tags: ["python", "preference", "conversation"]
"I work at Google" → tags: ["work", "conversation"]
```

---

## 🚀 **Usage in Chat**

### **Interactive Session:**

```bash
$ ai-memory chat

You: Hi! Remember that I'm a software engineer
AI: ✅ I'll remember that: "I'm a software engineer"
    Nice to meet you! What kind of software do you work on?

You: I build AI systems. Also, I drive a Tesla Model 3
AI: ✅ I'll remember that: "I drive a Tesla Model 3"
    Interesting! AI systems and Tesla - you're into cutting-edge tech!

You: What do you know about me?
AI: 📚 I found 2 memories:
    • I'm a software engineer
    • I drive a Tesla Model 3
    
    Based on what you've told me, you're a software engineer who builds
    AI systems and drives a Tesla Model 3. You seem to enjoy technology!

You: Forget about the Tesla
AI: 🗑️ I've forgotten about: "I drive a Tesla Model 3"
    Noted - I've removed that from my memory.

You: What do you know about me now?
AI: 📚 I found 1 memory:
    • I'm a software engineer
    
    You're a software engineer who builds AI systems.
```

**Everything happens naturally - no explicit commands needed!**

---

## 🔧 **Implementation Details**

### **File Created:**
`contextvault/services/command_interpreter.py`

### **Key Classes:**

**1. UserIntent (Enum):**
- REMEMBER, RECALL, FORGET, SEARCH, LIST, HELP, CHAT

**2. CommandInterpreter:**
- `detect_intent()` - Pattern matching to find intent
- `execute_intent()` - Run the appropriate action
- `format_for_context()` - Create optimal prompt for AI

**3. Helper Functions:**
- `_infer_type()` - Guess content type (preference/work/personal)
- `_extract_tags()` - Auto-generate tags from content
- `_extract_params()` - Pull out command parameters

---

## 🎯 **Integration in Chat Command**

### **Updated chat.py:**

```python
from ..services.command_interpreter import process_user_input

async def chat_loop():
    while True:
        user_input = input("You: ")
        
        # Process for natural language commands
        formatted_input, intent_result = await process_user_input(user_input)
        
        # If it was a command, show result immediately
        if intent_result.get("execute_command"):
            print(f"AI: {intent_result['message']}")
            
            # If it was recall/list, don't need AI response
            if intent_result["intent"] in ["recall", "list", "help"]:
                continue
        
        # Send to AI with formatted context
        response = await call_ai(formatted_input, model="llama3.1")
        print(f"AI: {response}")
```

---

## 📊 **Benefits**

### **User Experience:**

**Before:**
```
User must learn CLI syntax
User must know commands exist
User must type exact format
```

**After:**
```
User talks naturally
System detects intent
System executes automatically
```

### **Intelligence:**

**Before:**
```
AI: Just a chatbot
User: Has to manually manage memory
```

**After:**
```
AI: Proactively manages its own memory
User: Just talks naturally
System: Handles everything
```

---

## 🎓 **Example Conversations**

### **Conversation 1: Building Knowledge**

```
You: Hi, I'm Alice
AI: ✅ I'll remember that: "I'm Alice"
    Nice to meet you, Alice!

You: I love hiking and photography
AI: ✅ I'll remember that: "I love hiking and photography"
    Great hobbies! Do you go on photo hikes?

You: Yes! Last week I hiked Mount Tam
AI: ✅ I'll remember that: "Last week I hiked Mount Tam"
    Mount Tam is beautiful! Did you get good photos?

[System automatically saved 3 memories]
```

### **Conversation 2: Recalling Knowledge**

```
You: What do you know about my hobbies?
AI: 📚 I found 2 memories:
    • I love hiking and photography
    • Last week I hiked Mount Tam
    
    You enjoy hiking and photography! You recently hiked Mount Tam.

You: What's my name?
AI: 📚 I found 1 memory:
    • I'm Alice
    
    Your name is Alice!
```

### **Conversation 3: Managing Memory**

```
You: Remember that I prefer Python over JavaScript
AI: ✅ I'll remember that: "I prefer Python over JavaScript"
    Got it! Python it is.

You: Actually, I've changed my mind. Forget about that
AI: 🗑️ I've forgotten about: "I prefer Python over JavaScript"
    Alright, I've removed that preference.

You: Remember that I like both Python AND JavaScript now
AI: ✅ I'll remember that: "I like both Python AND JavaScript now"
    Nice! Open to both languages. That's flexible.
```

---

## 🚀 **Next Steps**

### **To Enable This:**

1. **Service is created:** `command_interpreter.py` ✅

2. **Integrate in chat.py:**
```python
# Update contextvault/cli/commands/chat.py
from ...services.command_interpreter import process_user_input

# In chat loop:
formatted, result = await process_user_input(user_input)
if result.get("execute_command"):
    console.print(result["message"])
```

3. **Test:**
```bash
ai-memory chat

You: Remember that I love Python
AI: ✅ I'll remember that...
```

---

## 📋 **Command Detection Patterns**

Full list of patterns the system recognizes:

**REMEMBER:**
- "remember that..."
- "store this..."
- "save that..."
- "keep in mind..."
- "note that..."
- "don't forget..."
- "I want you to know..."

**RECALL:**
- "what did I tell you about..."
- "do you remember..."
- "what do you know about..."
- "tell me about..."
- "what's my..."
- "remind me..."

**FORGET:**
- "forget about..."
- "delete..."
- "remove from memory..."
- "don't remember..."
- "erase..."

**SEARCH:**
- "search for..."
- "find in memory..."
- "look up..."

**LIST:**
- "what do you know about me?"
- "list everything you know"
- "show me all you've stored"
- "what have I told you?"

**HELP:**
- "what can you do?"
- "help"
- "how do I use this?"

---

## 🎯 **The Magic**

User doesn't need to know ANY commands!

They just chat naturally:
- "Remember X" → System stores X
- "What did I say about Y?" → System searches Y
- "Forget Z" → System deletes Z

**AI Memory becomes truly conversational!** 🎉

