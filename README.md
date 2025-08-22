# Hackathon Access System

This repository contains a modular, full-stack system for managing access and logistics at hackathon events. It streamlines participant management, event check-in, ticketing, and real-time analytics for facilitators, with a modern web interface and secure backend.

## Features

- **Facilitator Portal:** Web interface for event staff to manage participant workflows.
- **Authentication:** Secure login/signup for facilitators using JWT tokens and bcrypt password hashing.
- **QR Code Scanning:** Fast, camera-based check-in for Bus Boarding, Registration, and Meal Collection.
- **Ticket Management:** Download, resend, and validate participant tickets.
- **Participant Check-in:** Real-time check-in with attendance logging.
- **Analytics Dashboard:** View summary statistics on registration, check-ins, and participant types.
- **Supabase Integration:** Cloud database and serverless functions for scalability.
- **SweetAlert Feedback:** User-friendly, interactive alerts for all critical actions.

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL)
- **QR Scanner:** [html5-qrcode](https://github.com/mebjas/html5-qrcode)
- **Alerts:** [SweetAlert2](https://sweetalert2.github.io/)
- **Authentication:** JWT, bcrypt

## Usage

### 1. Facilitator Portal

- Log in or sign up as a facilitator.
- Use the sidebar navigation for:
  - Bus Boarding
  - Registration
  - Meal Collection
  - Reports (Analytics)

### 2. QR Code Scanning

- Navigate to the relevant workflow.
- Scan participant QR codes using your device camera.
- Actions are confirmed with instant feedback.

### 3. Ticket Management

- Download tickets for participants.
- Resend tickets via email.

### 4. Analytics

- View live summary of registrations, check-ins, and breakdown by participant type.

## Development

### Prerequisites

- Python 3.8+
- Node.js (for Supabase functions)
- Supabase project and API keys
- SMTP credentials for email (ticket sending)

### Environment Variables

Set the following in your `.env` or environment:

```
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_key
EMAIL_USER=your_email_address
EMAIL_PASS=your_email_password
SMTP_SERVER=smtp.yourprovider.com
SMTP_PORT=587
SECRET_KEY=your_jwt_secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Running Locally

1. **Backend:**
   - Install dependencies: `pip install -r requirements.txt`
   - Run FastAPI: `uvicorn main:app --reload`

2. **Frontend:**
   - Serve the `frontend/` directory with a static server or open `index.html` directly.

3. **Supabase Functions:**
   - Deploy or run with Deno (see `supabase/functions/boarding/index.js` for an example).

## File Structure

```
main.py                      # FastAPI backend (API endpoints)
frontend/
  ├── index.html             # Main facilitator portal UI
  ├── css/style.css          # Styles
  └── js/
      ├── app.js             # Frontend logic
      └── supabase.js        # API + auth helpers
supabase/
  └── functions/
      └── boarding/          # Example serverless function
```

## Security

- Facilitator authentication uses hashed passwords and JWT.
- API endpoints require valid tokens.
- Sensitive credentials are not hardcoded.
- User inputs are validated and errors handled with descriptive feedback.

## Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

MIT License

---

**Contact:** For questions, open an issue or reach out to the repository owner.
