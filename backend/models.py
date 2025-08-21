from pydantic import BaseModel


class TicketIssueRequest(BaseModel):
    participant_id: str
    full_name: str
    email: str
    student_number: str