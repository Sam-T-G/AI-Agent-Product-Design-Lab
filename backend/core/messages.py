"""Message-based communication system for agents."""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MessageType(Enum):
    """Types of messages agents can send."""
    DELEGATE = "delegate"  # Parent → Child: Assign task
    REPORT = "report"  # Child → Parent: Report results
    QUERY = "query"  # Child → Parent: Ask question
    ANSWER = "answer"  # Parent → Child: Answer question
    REQUEST_USER_INPUT = "request_user_input"  # Agent → User: Need info
    USER_RESPONSE = "user_response"  # User → Agent: Provide info
    ERROR = "error"  # Any → Any: Report error
    STATUS = "status"  # Any → Any: Status update


class AgentState(Enum):
    """States an agent can be in."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    WAITING_FOR_CHILD = "waiting_for_child"
    WAITING_FOR_PARENT = "waiting_for_parent"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    ERROR = "error"


class Message(BaseModel):
    """A message between agents or between agent and user."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    from_id: str  # agent_id or "user"
    to_id: str  # agent_id or "user"
    content: str
    context: Optional[Dict[str, Any]] = None
    requires_response: bool = False
    in_response_to: Optional[str] = None  # message_id this responds to
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class DelegateMessage(Message):
    """Parent delegates a task to a child."""
    message_type: MessageType = MessageType.DELEGATE
    task: str
    requires_response: bool = True
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('task', '')
        super().__init__(**data)


class ReportMessage(Message):
    """Child reports results back to parent."""
    message_type: MessageType = MessageType.REPORT
    result: str
    status: str  # "completed", "partial", "needs_help"
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('result', '')
        super().__init__(**data)


class QueryMessage(Message):
    """Child asks parent a question."""
    message_type: MessageType = MessageType.QUERY
    question: str
    requires_response: bool = True
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('question', '')
        super().__init__(**data)


class AnswerMessage(Message):
    """Parent answers child's question."""
    message_type: MessageType = MessageType.ANSWER
    answer: str
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('answer', '')
        super().__init__(**data)


class RequestUserInputMessage(Message):
    """Agent requests input from user."""
    message_type: MessageType = MessageType.REQUEST_USER_INPUT
    question: str
    to_id: str = "user"
    requires_response: bool = True
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('question', '')
        super().__init__(**data)


class UserResponseMessage(Message):
    """User provides requested input."""
    message_type: MessageType = MessageType.USER_RESPONSE
    from_id: str = "user"
    answer: str
    
    def __init__(self, **data):
        if 'content' not in data:
            data['content'] = data.get('answer', '')
        super().__init__(**data)


class MessageValidator:
    """Validates message exchanges."""
    
    @staticmethod
    def validate_delegate_report(delegate: DelegateMessage, report: ReportMessage) -> tuple[bool, str]:
        """
        Validate that a report appropriately addresses a delegate task.
        
        Returns:
            (is_valid, reason)
        """
        if not report.in_response_to == delegate.message_id:
            return False, "Report is not in response to this delegate"
        
        if report.status == "completed" and len(report.result) < 10:
            return False, "Report is too short to be meaningful"
        
        return True, "Valid response"
    
    @staticmethod
    def validate_query_answer(query: QueryMessage, answer: AnswerMessage) -> tuple[bool, str]:
        """
        Validate that an answer addresses a query.
        
        Returns:
            (is_valid, reason)
        """
        if not answer.in_response_to == query.message_id:
            return False, "Answer is not in response to this query"
        
        if len(answer.answer) < 3:
            return False, "Answer is too short"
        
        return True, "Valid response"
    
    @staticmethod
    def validate_user_response(request: RequestUserInputMessage, response: UserResponseMessage) -> tuple[bool, str]:
        """
        Validate that a user response addresses the request.
        
        Returns:
            (is_valid, reason)
        """
        if not response.in_response_to == request.message_id:
            return False, "Response is not in response to this request"
        
        if not response.answer.strip():
            return False, "User response is empty"
        
        return True, "Valid response"


class AgentMailbox:
    """Manages messages for an agent."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.inbox: List[Message] = []
        self.outbox: List[Message] = []
        self.pending_responses: Dict[str, Message] = {}
        self.current_state: AgentState = AgentState.IDLE
        
    def send(self, message: Message):
        """Send a message from this agent."""
        message.from_id = self.agent_id
        self.outbox.append(message)
        
        if message.requires_response:
            self.pending_responses[message.message_id] = message
    
    def receive(self, message: Message):
        """Receive a message to this agent."""
        self.inbox.append(message)
        
        # If this message is a response, remove from pending
        if message.in_response_to and message.in_response_to in self.pending_responses:
            del self.pending_responses[message.in_response_to]
    
    def get_unread_messages(self) -> List[Message]:
        """Get all unread messages."""
        messages = self.inbox.copy()
        self.inbox.clear()
        return messages
    
    def has_pending_responses(self) -> bool:
        """Check if waiting for any responses."""
        return len(self.pending_responses) > 0
    
    def get_pending_messages(self) -> List[Message]:
        """Get messages still waiting for response."""
        return list(self.pending_responses.values())
    
    def set_state(self, state: AgentState):
        """Update agent state."""
        self.current_state = state
    
    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.current_state

